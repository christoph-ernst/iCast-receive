const POLL_MS = 100;
const CONFIG_POLL_MS = 2000; // config changes are infrequent

let config = {};
const board = document.querySelector(".scoreboard");

function getMatchfacts() {
  return fetch(`match-facts.json?_=${Date.now()}`).then(r => r.json());
}

function getConfig() {
  return fetch(`config.json?_=${Date.now()}`).then(r => r.json());
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "";
}

function applyConfig(cfg) {
  const root = document.documentElement.style;
  if (cfg.home_accent) root.setProperty("--home-accent", cfg.home_accent);
  if (cfg.away_accent) root.setProperty("--away-accent", cfg.away_accent);
  config = cfg;
}

function updateCoreFields(mf) {
  setText("time_period", mf.time_period);
  setText("score", mf.score);
  setText("period", mf.period);
  // Config team names take priority over hardware values
  setText("home_team_name", config.home_team_name || mf.home_team_name);
  setText("guest_team_name", config.guest_team_name || mf.guest_team_name);
  setText("time_type", mf.time_type);
}

function updatePowerPlays(mf) {
  const left1Active = !!mf.guest_penalty_1;
  const left2Active = !!mf.guest_penalty_2;
  const right1Active = !!mf.home_penalty_1;
  const right2Active = !!mf.home_penalty_2;

  setText("pp_left_clock1", mf.guest_penalty_1 || "");
  setText("pp_left_clock2", mf.guest_penalty_2 || "");
  setText("pp_right_clock1", mf.home_penalty_1 || "");
  setText("pp_right_clock2", mf.home_penalty_2 || "");

  board.classList.toggle("has-pp-left1", left1Active);
  board.classList.toggle("has-pp-left2", left2Active);
  board.classList.toggle("has-pp-right1", right1Active);
  board.classList.toggle("has-pp-right2", right2Active);
}

// Poll match data (setTimeout recursion prevents overlapping fetches)
function pollMatchfacts() {
  getMatchfacts()
    .then(mf => { updateCoreFields(mf); updatePowerPlays(mf); })
    .catch(err => console.error("Could not fetch match facts:", err))
    .finally(() => setTimeout(pollMatchfacts, POLL_MS));
}
pollMatchfacts();

// Poll config (less frequently)
function pollConfig() {
  getConfig()
    .then(applyConfig)
    .catch(() => {}) // config.json missing is non-fatal
    .finally(() => setTimeout(pollConfig, CONFIG_POLL_MS));
}
pollConfig(); // start immediately, then recurse
