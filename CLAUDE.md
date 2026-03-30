# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

iCast-receive is a live unihockey scoreboard system. A Python UDP listener receives packets from scoreboard hardware, parses a custom protocol, and writes `match-facts.json` atomically. A browser-based overlay polls that file every 100ms and updates the DOM for broadcast display.

## Running

```bash
# Start UDP receiver (listens on 0.0.0.0:50078)
python3 iCast-receive.py

# Send test data (replays captured packets to localhost)
python3 send-data.py

# Serve the web overlay (also handles POST /config for config.html)
python3 serve.py
# Then open http://localhost:8000/index.html
# Configure teams/colors at http://localhost:8000/config.html
```

No external Python packages required — stdlib only (`socket`, `json`, `os`, `tempfile`). Requires Python 3.10+ (uses `X | Y` union type hints).

## Architecture

**Data flow:** UDP packet → `iCast-receive.py` → `match-facts.json` → `index.js` polls → DOM update

**Protocol:** Each character is encoded as 4 bytes (3 null bytes + character). Extraction: `data[3::4]`. Fields are semicolon-separated; minimum 13 fields required per packet.

**Atomic writes:** `write_json_atomic()` writes to a temp file then `os.replace()` to prevent partial reads by the browser.

**Power-play visibility:** All PP tiles are `visibility: hidden` by default. `index.js` toggles `.has-pp-left1/2` and `.has-pp-right1/2` classes on `.scoreboard` based on truthiness of penalty fields. CSS responds to these classes to show/hide tiles and the "PP" tag.

**Period labels:** `format_period_label()` maps the raw `time_type` field + period number to display strings (`1/3`, `2/3`, `3/3`, `OT`, `Pause`, `Time Out`).

**JSON contract** (fields written by `iCast-receive.py`, consumed by `index.js`):
- `time`, `score_home`, `score_guest`, `score`, `period`, `time_period`, `time_type`
- `home_team_name`, `guest_team_name`
- `home_penalty_1`, `home_penalty_2`, `guest_penalty_1`, `guest_penalty_2` (each `"MM:SS"` or `null`)

**Configuration:** `config.json` stores `home_team_name`, `guest_team_name`, `home_accent`, `away_accent`. Edited via `config.html` (POST `/config` handled by `serve.py`). `index.js` polls it every 2s; config team names override hardware values; colors are applied as CSS custom properties on `document.documentElement`.

**Test data:** `udp_payloads.py` contains byte-encoded packets extracted from `iCast-withPenalties.pcap` for use by `send-data.py`.
