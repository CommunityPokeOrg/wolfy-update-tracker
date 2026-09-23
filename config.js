// Wolfy Update Tracker — configuration
// The tracking window is fixed: 24 hours, measured in UTC+7 (Asia/Bangkok).
const CONFIG = {
  repoOwner: "CommunityPokeOrg",
  repoName: "wolfy-update-tracker",
  repoUrl: "https://github.com/CommunityPokeOrg/wolfy-update-tracker",

  // 24h tracking window (UTC). 15:30Z = 22:30 in UTC+7.
  trackingStart: "2026-09-23T15:30:00Z",
  trackingEnd: "2026-09-24T15:30:00Z",
  timezone: "Asia/Bangkok", // UTC+7

  pollMs: 30000,          // sightings refresh
  oddsPollMs: 60000,      // odds board refresh

  // Over/under lines, seeded as 👍/👎 reactions on odds-board issue comments.
  // One comment per line: 👍 = OVER, 👎 = UNDER.
  lines: [3.5, 7.5, 13.5, 21.5, 42.5],

  // Ban Risk Multiplier(TM): community-reported mod/admin omens (label: mod-omen)
  // within the last 48 hours, decayed and summed. Purely hypothetical.
  banWindowHours: 48,
  banDecayHalfLifeH: 18,  // omens fade: half weight every 18h
  strikeThreshold: 12,    // raw omen-points = one notional "mod strike"
};
