// index.js (replace everything with this)

const POLL_MS = 100; // adjust if you like

function getMatchfacts() {
  // cache-bust so we always get the latest file
  return fetch(`match-facts.json?_=${Date.now()}`).then(r => r.json());
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "";
}

function updateCoreFields(mf) {
  setText("time_period", mf.time_period);
  setText("score", mf.score);
  setText("period", mf.period);
  setText("home_team_name", mf.home_team_name);
  setText("guest_team_name", mf.guest_team_name);
  setText("time_type", mf.time_type);
}

function updatePowerPlays(mf) {
  const board = document.querySelector(".scoreboard");

  // LEFT (guest)
  const left1Active = !!mf.guest_penalty_1;
  const left2Active = !!mf.guest_penalty_2;

  // RIGHT (home)
  const right1Active = !!mf.home_penalty_1;
  const right2Active = !!mf.home_penalty_2;

  // Text
  setText("pp_left_clock1", mf.guest_penalty_1 || "");
  setText("pp_left_clock2", mf.guest_penalty_2 || "");
  setText("pp_right_clock1", mf.home_penalty_1 || "");
  setText("pp_right_clock2", mf.home_penalty_2 || "");

  // Classes to show/hide PP tiles via your CSS
  board.classList.toggle("has-pp-left1", left1Active);
  board.classList.toggle("has-pp-left2", left2Active);
  board.classList.toggle("has-pp-right1", right1Active);
  board.classList.toggle("has-pp-right2", right2Active);
}

function updateMatchfacts(mf) {
  updateCoreFields(mf);
  updatePowerPlays(mf);
}

// Poll and update UI
setInterval(() => {
  getMatchfacts()
    .then(updateMatchfacts)
    .catch(err => console.error("Could not fetch or update match facts:", err));
}, POLL_MS);
