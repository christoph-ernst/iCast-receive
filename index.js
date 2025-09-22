
/* iCast Overlay Client (wrapped JSON version)
   -------------------------------------------
   Expects match-facts.json with shape:
   {
     "received_at": <unix seconds>,
     "age_seconds": <float>,
     "match_facts": {
        "time","score_home","score_guest","score",
        "period","time_period",
        "home_penalty_1","home_penalty_2",
        "guest_penalty_1","guest_penalty_2",
        "home_team_name","guest_team_name","time_type","raw"
     }
   }
*/

(() => {
  const CONFIG = {
    url: "match-facts.json",
    pollMs: 500,               // how often we poll the JSON
    staleWarnSec: 3,           // add .is-stale if data age exceeds this
    requestTimeoutMs: 1500,    // network timeout for each fetch
    cacheBust: true
  };

  const root = document.querySelector(".scoreboard") || document.body;

  const $ = (sel) => document.querySelector(sel);
  const setText = (id, val) => {
    const el = document.getElementById(id);
    if (!el) return;
    const next = val == null ? "" : String(val);
    if (el.textContent !== next) el.textContent = next;
  };

  const setClass = (el, className, enabled) => {
    if (!el) return;
    if (enabled) el.classList.add(className);
    else el.classList.remove(className);
  };

  const withTimeout = (ms, promise) => {
    const ctrl = new AbortController();
    const to = setTimeout(() => ctrl.abort(), ms);
    return promise(ctrl.signal).finally(() => clearTimeout(to));
  };

  async function fetchFacts() {
    const make = (signal) => {
      const bust = CONFIG.cacheBust ? ((CONFIG.url.includes("?") ? "&" : "?") + "_ts=" + Date.now()) : "";
      return fetch(CONFIG.url + bust, { cache: "no-store", signal }).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      });
    };
    return withTimeout(CONFIG.requestTimeoutMs, make);
  }

  function applyFacts(payload) {
    if (!payload || typeof payload !== "object" || !payload.match_facts) return;

    const age = Number(payload.age_seconds || 0);
    setClass(root, "is-stale", age > CONFIG.staleWarnSec);

    const f = payload.match_facts;

    setText("home_team_name", f.home_team_name);
    setText("guest_team_name", f.guest_team_name);
    setText("score", f.score);
    setText("time_period", f.time_period);

    // Optional: document title as quick glance
    if (f.home_team_name && f.guest_team_name && f.score) {
      const desired = `${f.home_team_name} ${f.score} ${f.guest_team_name} — ${f.time_period || ""}`.trim();
      if (document.title !== desired) document.title = desired;
    }

    // Penalties (left = home, right = guest) - show/hide via classes on .scoreboard
    const left1 = !!f.home_penalty_1;
    const left2 = !!f.home_penalty_2;
    const right1 = !!f.guest_penalty_1;
    const right2 = !!f.guest_penalty_2;

    setText("pp_left_clock1", f.home_penalty_1);
    setText("pp_left_clock2", f.home_penalty_2);
    setText("pp_right_clock1", f.guest_penalty_1);
    setText("pp_right_clock2", f.guest_penalty_2);

    setClass(root, "has-pp-left1", left1);
    setClass(root, "has-pp-left2", left2);
    setClass(root, "has-pp-right1", right1);
    setClass(root, "has-pp-right2", right2);
  }

  function applyError(err) {
    console.warn("[overlay] fetch error:", err && err.message ? err.message : err);
    setClass(root, "is-stale", true);
  }

  let ticking = false;
  async function tick() {
    if (ticking) return;
    ticking = true;
    try {
      const data = await fetchFacts();
      applyFacts(data);
    } catch (e) {
      applyError(e);
    } finally {
      ticking = false;
    }
  }

  // Start polling
  tick();
  setInterval(tick, CONFIG.pollMs);
})();
