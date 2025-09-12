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
-   The page loads `index.js` to update the DOM---e.g., filling
    `#home_team_name`, `#guest_team_name`, `#score`, and
    `#time_period`---typically by reading `match-facts.json` on an
    interval.

------------------------------------------------------------------------

## File structure

    iCast-receive.py   # UDP listener → match-facts.json (atomic)
    index.html         # Scoreboard layout (DOM IDs for live data)
    index.css          # Broadcast-ready styling + PP visibility classes
    index.js           # Client logic that refreshes the overlay (DOM updates)

------------------------------------------------------------------------

## Running it locally

### Requirements

-   Python 3.10+ (for type hints/union operator) and network access to
    the scoreboard sender.
-   Any static file server for the web overlay (or open `index.html`
    directly).

### 1) Start the UDP receiver

``` bash
python3 iCast-receive.py
```

You should see "Starting UDP server on port 50078..." and new
**`match-facts.json`** snapshots appearing as packets arrive.

### 2) Open the overlay

-   Serve the folder (e.g., `python3 -m http.server 8000`) and open
    `http://localhost:8000/index.html`, or just open `index.html` in a
    browser.
-   Ensure the page's script can read `match-facts.json` (same
    directory/origin recommended). DOM placeholders are already in the
    HTML: `#home_team_name`, `#guest_team_name`, `#score`,
    `#time_period`, and PP clocks like `#pp_left_clock1`.

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

## Customization

-   **Colors & layout:** adjust CSS variables (`--home-accent`,
    `--away-accent`, `--score-bg`, font sizes, tile heights).
-   **PP visibility:** toggle `.scoreboard.has-pp-left1/2` or
    `.has-pp-right1/2` based on current penalties to show/hide PP tiles.
-   **Period labeling:** tweak `format_period_label()` if your
    controller uses different tokens for overtime or intermission.

------------------------------------------------------------------------

## Notes & gotchas

-   **Atomic JSON writes:** consumers can safely poll `match-facts.json`
    without race conditions.
-   **Malformed packets:** the receiver logs and skips packets that
    can't be decoded/parsed.
-   **CORS/file access:** if loading the overlay from `file://`, some
    browsers restrict XHR/fetch. Prefer a local static server for
    reading `match-facts.json`.

------------------------------------------------------------------------

## License

This project is licensed under the GNU GENERAL PUBLIC LICENSE Version 3. See the LICENSE file for details.
