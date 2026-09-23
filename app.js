/* Wolfy Update Tracker — live tally, odds board, Ban Risk Multiplier(TM).
   Data source: public GitHub issues + reactions on this repo. No backend, no auth.
   Conditional requests (ETag) are used so repeated polling is cheap. */

const API = `https://api.github.com/repos/${CONFIG.repoOwner}/${CONFIG.repoName}`;
const $ = (id) => document.getElementById(id);

const START = new Date(CONFIG.trackingStart);
const END = new Date(CONFIG.trackingEnd);
const HOUR = 3600e3;

const etags = new Map(); // url -> etag (in-memory; 304s don't burn rate limit)

async function gh(url) {
  const headers = { Accept: "application/vnd.github+json" };
  if (etags.has(url)) headers["If-None-Match"] = etags.get(url);
  const res = await fetch(url, { headers });
  if (res.status === 304 && ghCache.has(url)) return ghCache.get(url);
  if (!res.ok) {
    if (res.status === 403) throw new Error("rate-limited");
    throw new Error(`GitHub API ${res.status}`);
  }
  const etag = res.headers.get("ETag");
  if (etag) etags.set(url, etag);
  const data = await res.json();
  ghCache.set(url, data);
  return data;
}
const ghCache = new Map();

/* ---------- links ---------- */
const newIssueBase = `https://github.com/${CONFIG.repoOwner}/${CONFIG.repoName}/issues/new`;
$("reportBtn").href = `${newIssueBase}?template=sighting.yml`;
$("omenBtn").href = `${newIssueBase}?template=mod-omen.yml`;
$("repoLink").href = CONFIG.repoUrl;

/* ---------- parsing helpers ---------- */
// Issue-form bodies render as "### Label\n\nvalue\n\n### Next label..."
function fieldValue(body, labelStart) {
  if (!body) return "";
  const re = new RegExp(`###\\s*${labelStart}[^\\n]*\\n([\\s\\S]*?)(?=\\n###|$)`, "i");
  const m = body.match(re);
  return m ? m[1].trim() : "";
}
function firstInt(text, fallback) {
  const m = (text || "").match(/\d+/);
  return m ? parseInt(m[0], 10) : fallback;
}
function esc(s) {
  return (s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const fmtTZ = (d) =>
  new Intl.DateTimeFormat("fi-FI", {
    timeZone: CONFIG.timezone, day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  }).format(d);

/* ---------- clock + countdown ---------- */
function tick() {
  const now = new Date();
  $("localClock").textContent = new Intl.DateTimeFormat("fi-FI", {
    timeZone: CONFIG.timezone, hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).format(now);

  const remain = END - now;
  const total = END - START;
  if (remain <= 0) {
    $("countdown").textContent = "00:00:00";
    $("progressBar").style.width = "100%";
    document.title = "🐺 TIME'S UP — Wolfy Update Tracker";
  } else {
    const h = Math.floor(remain / HOUR);
    const m = Math.floor((remain % HOUR) / 60e3);
    const s = Math.floor((remain % 60e3) / 1e3);
    $("countdown").textContent =
      `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    $("progressBar").style.width = `${Math.min(100, ((now - START) / total) * 100)}%`;
  }
}
$("startTime").textContent = fmtTZ(START) + " UTC+7";
$("endTime").textContent = fmtTZ(END) + " UTC+7";
setInterval(tick, 1000);
tick();

/* ---------- sightings ---------- */
let lastCount = -1;
let sightings = [];

async function loadSightings() {
  try {
    const issues = await gh(
      `${API}/issues?labels=sighting&state=all&per_page=100&sort=created&direction=desc`);
    sightings = issues.filter((i) => !i.pull_request).map((i) => ({
      n: i.number,
      title: i.title,
      who: i.user ? i.user.login : "anonymous",
      at: new Date(i.created_at),
      count: firstInt(fieldValue(i.body, "How many"), 1),
      quote: fieldValue(i.body, "What did Wolfy say").replace(/^"|"$/g, ""),
    }));
    renderSightings();
    $("feedStatus").textContent =
      `last refreshed ${new Date().toLocaleTimeString()} · ${sightings.length} sightings on record`;
  } catch (e) {
    $("feedStatus").textContent =
      `refresh hiccup (${e.message}) — the wolf endures; retrying soon`;
  }
}

function renderSightings() {
  const total = sightings.reduce((a, s) => a + s.count, 0);
  const el = $("tickerCount");
  if (lastCount >= 0 && total > lastCount) {
    el.classList.remove("bump"); void el.offsetWidth; el.classList.add("bump");
    confetti();
  }
  lastCount = total;
  el.textContent = total;

  // pace / projection
  const now = Date.now();
  const elapsedH = Math.max((now - START) / HOUR, 0.01);
  const remainH = Math.max((END - now) / HOUR, 0);
  const pace = total / Math.min(elapsedH, 24);
  const proj = total + pace * remainH;
  $("paceLine").textContent = total === 0
    ? "Waiting for the first “update”… the silence is deafening."
    : `pace ${pace.toFixed(2)}/h → projected ${proj.toFixed(1)} updates by closing time`;

  drawSparkline();
  renderKuitti(total);
}

function drawSparkline() {
  const c = $("sparkline");
  const dpr = window.devicePixelRatio || 1;
  const w = c.clientWidth || 300, h = 64;
  c.width = w * dpr; c.height = h * dpr;
  const ctx = c.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  const buckets = new Array(24).fill(0);
  for (const s of sightings) {
    const bh = Math.floor((s.at - START) / HOUR);
    if (bh >= 0 && bh < 24) buckets[bh] += s.count;
  }
  const max = Math.max(...buckets, 1);
  const bw = w / 24;
  buckets.forEach((v, i) => {
    const bh = (v / max) * (h - 8);
    ctx.fillStyle = v > 0 ? "#ff8c1a" : "#4a361866";
    ctx.beginPath();
    ctx.roundRect(i * bw + 2, h - bh, bw - 4, bh, 3);
    ctx.fill();
  });
}

function renderKuitti(total) {
  const items = $("kuittiItems");
  if (!sightings.length) {
    items.innerHTML = `<div class="kuitti-empty">— ei havaintoja vielä —<br>(grillijono odottaa)</div>`;
  } else {
    items.innerHTML = sightings.map((s) => {
      const desc = s.quote
        ? `&quot;${esc(s.quote).slice(0, 60)}&quot;`
        : esc(s.title.replace(/^🐺\s*/, "").slice(0, 44));
      return `<div class="kuitti-item" title="#${s.n} by ${esc(s.who)}">
        <span class="desc">${fmtTZ(s.at)} ${desc}</span>
        <span class="qty">${s.count}× upd</span>
      </div>`;
    }).join("");
  }
  $("kuittiTotal").textContent =
`------------------------------
YHTEENSÄ / TOTAL:    ${total} update${total === 1 ? "" : "s"}
MAKSETTU: grillikuiteilla
KIITOS JA AUKI HUOMISEEN
Tervetuloa K-Rautaan!
------------------------------`;
}

/* ---------- odds board ---------- */
const LINE_JOKES = [
  "litasitko liian aikaisin?",
  "koira haistaa päivityksen",
  "house edge: makkaraa",
  "las Vegas wishes",
  "the Whaley's line",
];

async function loadOdds() {
  try {
    const issues = await gh(`${API}/issues?labels=odds&state=open&per_page=5`);
    const board = issues.find((i) => !i.pull_request);
    if (!board) { $("oddsStatus").textContent = "odds board missing — house is renovating"; return; }
    $("oddsLink").href = board.html_url;
    const comments = await gh(`${API}/issues/${board.number}/comments?per_page=100`);
    renderOdds(comments);
    $("oddsStatus").textContent = "odds update every minute · 👍/👎 reactions are the bets";
  } catch (e) {
    $("oddsStatus").textContent = `odds refresh hiccup (${e.message}) — bookie is at the grill`;
  }
}

function renderOdds(comments) {
  const grid = $("oddsGrid");
  const byLine = new Map();
  for (const c of comments) {
    const m = (c.body || "").match(/<!--\s*line:([\d.]+)\s*-->/);
    if (m) byLine.set(parseFloat(m[1]), c);
  }
  let hottest = -1, hotVol = -1;
  const cards = CONFIG.lines.map((line, i) => {
    const c = byLine.get(line);
    const over = c ? (c.reactions["+1"] || 0) : 0;
    const under = c ? (c.reactions["-1"] || 0) : 0;
    const sum = over + under;
    if (sum > hotVol) { hotVol = sum; hottest = i; }
    const op = sum ? Math.round((over / sum) * 100) : 50;
    const up = 100 - op;
    return { line, over, under, op, up, joke: LINE_JOKES[i % LINE_JOKES.length], sum };
  });
  grid.innerHTML = cards.map((c, i) => `
    <div class="odds-card${i === hottest && c.sum > 0 ? " hot" : ""}">
      <div class="line">O/U ${c.line} <small>updates</small></div>
      <div class="split-bar">
        <div class="over" style="width:${c.op}%"></div>
        <div class="under" style="width:${c.up}%"></div>
      </div>
      <div class="pct"><span class="o">OVER ${c.op}% (${c.over})</span><span class="u">(${c.under}) ${c.up}% UNDER</span></div>
      <div class="funny">${c.joke} · ${c.sum} bet${c.sum === 1 ? "" : "s"}</div>
    </div>`).join("");
}

/* ---------- Ban Risk Multiplier(TM) ---------- */
function banVerdict(mult, dist, n) {
  if (n === 0) return "No omens on record. Either the mods are asleep or the trap is set.";
  if (dist >= 0.8) return "Code red. Wolfy is one 'update' away from becoming a cautionary tale.";
  if (dist >= 0.5) return "The mods are circling like seagulls over a grill queue.";
  if (dist >= 0.25) return "Mild menace detected. Mia has been seen typing, then deleting.";
  return "Low-level grumbling. Statistically, Wolfy is fine. Spiritually, unclear.";
}
const VOL_LABELS = ["Flat", "Twitchy", "Spicy", "Chaotic", "Mia-tier"];

async function loadBanRisk() {
  try {
    const issues = await gh(`${API}/issues?labels=mod-omen&state=all&per_page=100`);
    const cutoff = Date.now() - CONFIG.banWindowHours * HOUR;
    const omens = issues.filter((i) => !i.pull_request && new Date(i.created_at) >= cutoff)
      .map((i) => ({
        n: i.number,
        mod: fieldValue(i.body, "Which mod") || "a mod",
        text: fieldValue(i.body, "What did they say"),
        menace: Math.min(5, Math.max(1, firstInt(fieldValue(i.body, "Menace level"), 3))),
        at: new Date(i.created_at),
      })).sort((a, b) => b.at - a.at);
    renderBanRisk(omens);
  } catch (e) {
    $("banVerdict").textContent = `omen feed unreachable (${e.message}) — assuming the worst`;
  }
}

function renderBanRisk(omens) {
  const now = Date.now();
  let raw = 0;
  for (const o of omens) {
    const ageH = (now - o.at) / HOUR;
    raw += o.menace * Math.pow(0.5, ageH / CONFIG.banDecayHalfLifeH);
  }
  const mult = 1 + raw / 5;
  const dist = Math.min(1, raw / CONFIG.strikeThreshold);
  $("banMultiplier").textContent = `×${mult.toFixed(2)}`;
  $("banVerdict").textContent = banVerdict(mult, dist, omens.length);
  $("strikeFill").style.width = `${dist * 100}%`;

  // volatility = stddev of menace, normalized to 0..1 over [0,2]
  const lv = omens.map((o) => o.menace);
  const mean = lv.reduce((a, b) => a + b, 0) / (lv.length || 1);
  const sd = Math.sqrt(lv.reduce((a, b) => a + (b - mean) ** 2, 0) / (lv.length || 1));
  const vol = Math.min(1, sd / 2);
  const vi = Math.min(VOL_LABELS.length - 1, Math.floor(vol * VOL_LABELS.length));
  $("volLabel").textContent = omens.length ? `${VOL_LABELS[vi]} (${sd.toFixed(2)})` : "—";
  $("volFill").style.width = `${(omens.length ? vol : 0) * 100}%`;
  $("volNote").textContent = omens.length
    ? `${omens.length} omen${omens.length === 1 ? "" : "s"} in ${CONFIG.banWindowHours}h, avg menace ${mean.toFixed(1)}/5`
    : "no data → volatility unknown, which is itself volatile";

  $("omenList").innerHTML = omens.length
    ? omens.slice(0, 8).map((o) => `<li>
        <span class="who">${esc(o.mod)}</span>
        <span class="menace">[${o.menace}/5]</span>
        ${esc(o.text).slice(0, 70)}
        <span class="when">${fmtTZ(o.at)}</span>
      </li>`).join("")
    : `<li class="empty">No omens reported. Mia has not joked about “Updates” in 48h. Suspicious.</li>`;
}

/* ---------- lore marquee ---------- */
const LORE = [
  "🧾 GRILLIKUITTI: 1× UPDATE — €0.00 — SIS. ALV 14%",
  "🔧 K-RAUTA REMINDER: 'update' ei löydy hyllystä, kysy henkilökunnalta",
  "🌭 makkara paistuu, Wolfy päivittää",
  "📦 SKU 404-UPDATE: varastossa 0 kpl, tilattavissa",
  "🐺 tally so far is audited by three wolves and a receipt printer",
  "⚠️ Ban Risk Multiplier™ is hypothetical — your actual mileage may be banned",
  "🛠️ K-Rauta auki 7–21, Wolfy auki aina",
  "🧾 palautusoikeus 14 päivää, päivityksiin ei palautusoikeutta",
];
$("loreMarquee").textContent = "  ·  " + LORE.join("  ·  ") + "  ·  " + LORE.join("  ·  ");

/* ---------- confetti ---------- */
function confetti() {
  const c = $("confetti");
  const ctx = c.getContext("2d");
  c.width = innerWidth; c.height = innerHeight;
  const parts = Array.from({ length: 140 }, () => ({
    x: Math.random() * c.width, y: -20 - Math.random() * c.height * .3,
    vy: 2 + Math.random() * 4, vx: -1.5 + Math.random() * 3,
    s: 4 + Math.random() * 6, r: Math.random() * Math.PI,
    vr: -0.1 + Math.random() * 0.2,
    col: ["#ffb347", "#ff8c1a", "#ff5d5d", "#7dd87d", "#f5e6c8"][Math.floor(Math.random() * 5)],
  }));
  let frames = 0;
  (function anim() {
    ctx.clearRect(0, 0, c.width, c.height);
    for (const p of parts) {
      p.x += p.vx; p.y += p.vy; p.r += p.vr;
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r);
      ctx.fillStyle = p.col; ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * .6);
      ctx.restore();
    }
    if (++frames < 220) requestAnimationFrame(anim);
    else ctx.clearRect(0, 0, c.width, c.height);
  })();
}

/* ---------- boot ---------- */
loadSightings(); setInterval(loadSightings, CONFIG.pollMs);
loadOdds(); setInterval(loadOdds, CONFIG.oddsPollMs);
loadBanRisk(); setInterval(loadBanRisk, CONFIG.pollMs);
