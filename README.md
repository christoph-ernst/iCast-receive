# iCast Scoreboard Receiver & Web Overlay

A tiny end-to-end setup for live unihockey scoreboards:

-   A Python UDP listener ingests datagrams from a scoreboard
    controller, parses the payload, and writes a `match-facts.json`
    snapshot atomically.
-   A lightweight HTML/CSS overlay renders the current game state
    (teams, score, time/period) and power-play tiles suitable for
    broadcast or streaming graphics.

------------------------------------------------------------------------

## How it works

### 1) UDP → JSON (Python)

-   Listens on **UDP port 50078** on all interfaces.
-   The incoming packet uses a custom 4-byte char encoding which is received and parsed.
-   Expected message format is a **semicolon-separated** string with at
    least 13 fields. Relevant fields are mapped into a JSON object and
    written to `match-facts.json` using an **atomic write** (temp file +
    `os.replace`) so readers never see a partial file.
-   Supports a configurable **broadcast delay**: reads `delay_tenths`
    from `config.json` every 2 seconds and schedules writes via
    `threading.Timer`, so the overlay lags live action by the configured
    amount without dropping packets.

The JSON keys produced:

    {
      "time", "score_home", "score_guest", "score",
      "period", "time_period",
      "home_penalty_1", "home_penalty_2",
      "guest_penalty_1", "guest_penalty_2",
      "home_team_name", "guest_team_name",
      "time_type"
    }

-   `time_period` formats period labels like `MM:SS  1/3`, `2/3`, `3/3`,
    or `OT`; intermissions show `Pause`; time-outs show `Time Out`.
-   Penalty fields are normalized to just the **penalty time** (last
    token) or `null` if absent.

### 2) Web Overlay (HTML/CSS/JS)

-   `index.html` defines a 9-column grid scoreboard with:
    -   Home team, center score, away team (top row)
    -   Optional **power-play tiles** (two per side) and a "PP" tag on
        each side
    -   A second row for **game clock / period** (`#time_period`)
-   `index.css` styles the board for broadcast use (bold teams, center
    score bar, team-colored side stripes). Power-play tiles are hidden
    by default and revealed by toggling container classes such as
    `.scoreboard.has-pp-left1`, `.has-pp-right2`, etc.
-   `index.js` polls `match-facts.json` every **100 ms** and
    `config.json` every **2 s**, updating the DOM for team names, score,
    period/clock, and PP tile visibility. Config team names and accent
    colors override hardware values; colors are applied as CSS custom
    properties (`--home-accent`, `--away-accent`) on the root element.

### 3) Configuration UI (`config.html`)

-   Served by `serve.py` at `http://localhost:8000/config.html`.
-   Lets operators set **team names**, **accent colors** (color picker +
    hex input with live preview), and **broadcast delay** (in tenths of
    a second) without editing files by hand.
-   Submits a `POST /config` request; `serve.py` validates and writes
    `config.json` atomically. `iCast-receive.py` picks up delay changes
    within 2 seconds; `index.js` picks up name/color changes within 2 s.

------------------------------------------------------------------------

## File structure

    iCast-receive.py   # UDP listener → match-facts.json (atomic, delay-aware)
    serve.py           # Static file server + POST /config handler
    index.html         # Scoreboard layout (DOM IDs for live data)
    index.css          # Broadcast-ready styling + PP visibility classes
    index.js           # Polls match-facts.json (100 ms) and config.json (2 s)
    config.html        # Operator UI for team names, accent colors, delay
    config.json        # Persisted config (team names, accent colors, delay_tenths)
    send-data.py       # Replays captured UDP packets for local testing
    udp_payloads.py    # Byte-encoded packets from iCast-withPenalties.pcap

------------------------------------------------------------------------

## Running it locally

### Requirements

-   Python 3.10+ (stdlib only — no external packages needed).
-   Network access to the scoreboard hardware, or use `send-data.py`
    for local testing.

### 1) Start the UDP receiver

``` bash
python3 iCast-receive.py
```

You should see "Starting UDP server on port 50078..." and new
**`match-facts.json`** snapshots appearing as packets arrive.

### 2) Start the web server

``` bash
python3 serve.py
```

This replaces a plain `http.server`; it also handles `POST /config` for
the configuration page.

### 3) Open the overlay and config page

-   Overlay: `http://localhost:8000/index.html`
-   Configuration: `http://localhost:8000/config.html`

### 4) Send test data (optional)

``` bash
python3 send-data.py
```

Replays captured packets to `localhost:50078` so you can test the
overlay without hardware.

------------------------------------------------------------------------

## Protocol details (receiver expects)

-   **Transport:** UDP, port **50078**.
-   **Encoding quirk:** each character is sent as 4 bytes; the last byte
    is the character. The script extracts every fourth byte starting at
    index 3.
-   **Payload:** semicolon-separated fields; at least 13 fields. Mapped
    fields include scores, time, period, team names, time-type ("GAME
    TIME", "INTERMISSION", "TIME-OUT"), and optional penalty descriptors
    from which only the time is retained.

------------------------------------------------------------------------

## Configuration reference (`config.json`)

| Key | Type | Description |
|---|---|---|
| `home_team_name` | string | Home team display name (overrides hardware) |
| `guest_team_name` | string | Away team display name (overrides hardware) |
| `home_accent` | `#rrggbb` | Home side stripe color |
| `away_accent` | `#rrggbb` | Away side stripe color |
| `delay_tenths` | integer | Broadcast delay in tenths of a second (0 = live) |

Edit via `config.html` or by POSTing JSON to `/config`.

------------------------------------------------------------------------

## Customization

-   **Colors:** set `--home-accent` / `--away-accent` via `config.html`
    or directly in `index.css`.
-   **PP visibility:** `index.js` toggles `.has-pp-left1/2` and
    `.has-pp-right1/2` on `.scoreboard` automatically based on penalty
    fields.
-   **Period labeling:** tweak `format_period_label()` in
    `iCast-receive.py` if your controller uses different tokens for
    overtime or intermission.

------------------------------------------------------------------------

## Notes & gotchas

-   **Atomic JSON writes:** consumers can safely poll `match-facts.json`
    without race conditions.
-   **Broadcast delay:** `delay_tenths` is re-read from `config.json`
    every 2 s without restarting the receiver. Each delayed write is
    scheduled via `threading.Timer`; in-flight timers are not cancelled
    when the delay is changed.
-   **Malformed packets:** the receiver logs and skips packets that
    can't be decoded/parsed.
-   **CORS/file access:** `serve.py` must be used (not `file://`) so
    `fetch()` calls for `match-facts.json` and `config.json` work
    correctly.

------------------------------------------------------------------------

## License

This project is licensed under the GNU GENERAL PUBLIC LICENSE Version 3. See the LICENSE file for details.
