
#!/usr/bin/env python3

"""
iCast Scoreboard Receiver (Threaded)
------------------------------------
Separates UDP receiving and JSON output into two threads:

- Receiver thread:
    * Listens on UDP and timestamps each datagram.
    * Pushes (timestamp, bytes) into a shared queue (deque).

- Writer thread:
    * Periodically purges items older than a configurable retention window.
    * Takes the newest remaining datagram and writes it to `match-facts.json`
      using an atomic write (temp file + os.replace).

Retention is configured in *centiseconds* (1/100th second) via RETENTION_CS.
"""

import socket
import threading
import time
import json
import os
import tempfile
import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Tuple, Optional, Dict, Any, List

# ---------------------- Configuration ----------------------

@dataclass
class Config:
    host: str = "0.0.0.0"
    port: int = 50078
    output_path: str = "match-facts.json"
    retention_cs: int = 1000      # MIN time to keep items in queue (100 = 1s; 1000 = 10s) 
    writer_poll_ms: int = 20      # writer checks every N milliseconds
    udp_bufsize: int = 4096
    debug: bool = False            # enable debug logging

CFG = Config()

# ---------------------- Shared queue -----------------------

class TimedQueue:
    """Thread-safe deque of (timestamp_seconds, raw_bytes)."""
    def __init__(self) -> None:
        self._dq: Deque[Tuple[float, bytes]] = deque()
        self._lock = threading.Lock()

    def push(self, ts: float, payload: bytes, debug: bool=False) -> None:
        with self._lock:
            self._dq.append((ts, payload))
        if debug:
            try:
                decoded = decode_payload(payload)
            except Exception:
                decoded = "<decode-error>"
            print(f"[DEBUG] PUSH @ {ts:.3f} | {len(payload)} bytes | decoded='{decoded}'")

    def purge_older_than(self, cutoff_ts: float) -> None:
        with self._lock:
            while self._dq and self._dq[0][0] < cutoff_ts:
                self._dq.popleft()

    def pop_latest_matured(self, cutoff_ts: float, debug: bool=False) -> Optional[Tuple[float, bytes]]:
        latest: Optional[Tuple[float, bytes]] = None
        removed = 0
        with self._lock:
            # Pop from LEFT while items are mature
            while self._dq and self._dq[0][0] <= cutoff_ts:
                latest = self._dq.popleft()
                removed += 1
        if latest and debug:
            ts, payload = latest
            try:
                decoded = decode_payload(payload)
            except Exception:
                decoded = "<decode-error>"
            print(f"[DEBUG] POP  @ {ts:.3f} | matured count this cycle={removed} | decoded='{decoded}'")
        return latest


    def size(self) -> int:
        with self._lock:
            return len(self._dq)

# ---------------------- Helpers ----------------------------

def atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically to avoid readers seeing partial files."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except FileNotFoundError:
            pass

def decode_payload(raw: bytes) -> str:
    """
    The iCast packets encode each character as 4 bytes, with the 4th byte
    being the ASCII character. We extract every 4th byte starting at index 3.
    If your sender changes, adjust this function.
    """
    if not raw:
        return ""
    try:
        meaningful = raw[3::4]
        return meaningful.decode("ascii", errors="ignore")
    except Exception:
        # Fall back to plain ASCII decode if above fails
        return raw.decode("ascii", errors="ignore")

def parse_message_to_match_facts(decoded: str) -> Dict[str, Any]:
    """
    Convert the semicolon-separated string into the JSON structure expected by the overlay.
    This mirrors the previous script's behavior as closely as possible, while being defensive.
    Unknown/missing fields are left as None.

    Expected keys:
      time, score_home, score_guest, score, period, time_period,
      home_penalty_1, home_penalty_2, guest_penalty_1, guest_penalty_2,
      home_team_name, guest_team_name, time_type
    """
    # Defaults
    facts: Dict[str, Any] = {
        "time": None,
        "score_home": None,
        "score_guest": None,
        "score": None,
        "period": None,
        "time_period": None,
        "home_penalty_1": None,
        "home_penalty_2": None,
        "guest_penalty_1": None,
        "guest_penalty_2": None,
        "home_team_name": None,
        "guest_team_name": None,
        "time_type": None,
        "raw": decoded,  # keep original for debugging
    }

    parts = [p.strip() for p in decoded.split(";")]
    # The actual index layout may vary by sender/config.
    # Below is a conservative mapping used by many iCast setups; tweak as needed.
    def safe_get(i: int) -> Optional[str]:
        return parts[i] if 0 <= i < len(parts) and parts[i] != "" else None

    # Attempt to locate common fields (best-effort mapping).
    # If your exact field order is known, replace these indices accordingly.
    facts["time"] = safe_get(0)  # e.g., "12:34"
    facts["score_home"] = safe_get(1)
    facts["score_guest"] = safe_get(2)
    if facts["score_home"] is not None and facts["score_guest"] is not None:
        facts["score"] = f'{facts["score_home"]}:{facts["score_guest"]}'

    facts["period"] = safe_get(3)         # e.g., "1", "2", "3", "OT"
    facts["time_type"] = safe_get(12)      # e.g., "GAME TIME", "INTERMISSION", "TIME-OUT"
    facts["home_team_name"] = safe_get(10)
    facts["guest_team_name"] = safe_get(11)

    # Penalties (free-form tokens; keep last token if it looks like a clock)
    def normalize_pen(v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        toks = v.split()
        if toks:
            cand = toks[-1]
            if ":" in cand:
                return cand
        return v

    facts["home_penalty_1"] = normalize_pen(safe_get(4))
    facts["home_penalty_2"] = normalize_pen(safe_get(5))
    facts["guest_penalty_1"] = normalize_pen(safe_get(6))
    facts["guest_penalty_2"] = normalize_pen(safe_get(7))

    # Build time_period label
    period_raw = facts["period"] or ""
    clock = facts["time"] or ""
    label = None
    if facts["time_type"] in ("INTERMISSION", "PAUSE"):
        label =  f"{clock} Pause"
    elif facts["time_type"] in ("TIME-OUT", "TIMEOUT"):
        label = "Time Out"
    else:
        if period_raw.upper() in ("4"):
            label = f"{clock}  OT" if clock else "OT"
        elif period_raw:
            label = f"{clock}  {period_raw}/3" if clock else f"{period_raw}/3"
        else:
            label = clock or None
    facts["time_period"] = label

    return facts

# ---------------------- Threads ----------------------------

def receiver_thread(cfg: Config, q: TimedQueue, stop: threading.Event) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((cfg.host, cfg.port))
        print(f"[receiver] Listening on {cfg.host}:{cfg.port}")
        while not stop.is_set():
            try:
                s.settimeout(0.5)
                data, _addr = s.recvfrom(cfg.udp_bufsize)
                ts = time.time()
                q.push(ts, data, debug=cfg.debug)

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[receiver] Error: {e}")



def writer_thread(cfg: Config, q: TimedQueue, stop: threading.Event) -> None:
    interval = max(1, cfg.writer_poll_ms) / 1000.0
    retention_s = max(0, cfg.retention_cs) / 100.0
    print(f"[writer] Poll interval: {interval:.3f}s  |  Min retention: {retention_s:.2f}s")
    while not stop.is_set():
        now = time.time()
        cutoff = now - retention_s
        # Only pop items that have matured long enough
        item = q.pop_latest_matured(cutoff_ts=cutoff, debug=cfg.debug)
        if item:
            ts, raw = item
            decoded = decode_payload(raw)
            facts = parse_message_to_match_facts(decoded)
            out = {
                "received_at": ts,
                "age_seconds": max(0.0, now - ts),
                "match_facts": facts,
            }
            try:
                atomic_write_json(cfg.output_path, out)
            except Exception as e:
                print(f"[writer] Write error: {e}")
        time.sleep(interval)

# ---------------------- Entry point ------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="iCast threaded receiver with enforced queue retention")
    parser.add_argument("--debug", action="store_true", help="Enable debug printing for push/pop")
    parser.add_argument("--retention-cs", type=int, help="Retention time in centiseconds (override config)")
    parser.add_argument("--writer-poll-ms", type=int, help="Writer poll interval in milliseconds (override config)")
    args = parser.parse_args()

    if args.retention_cs is not None:
        CFG.retention_cs = max(0, args.retention_cs)
    if args.writer_poll_ms is not None:
        CFG.writer_poll_ms = max(1, args.writer_poll_ms)
    CFG.debug = args.debug

    q = TimedQueue()
    stop = threading.Event()

    recv_t = threading.Thread(target=receiver_thread, args=(CFG, q, stop), name="receiver", daemon=True)
    writ_t = threading.Thread(target=writer_thread, args=(CFG, q, stop), name="writer", daemon=True)

    recv_t.start()
    writ_t.start()

    print(f"Starting UDP server on port {CFG.port} with MIN retention {CFG.retention_cs} cs.")
    print(f"Writing JSON to {CFG.output_path}")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        stop.set()
        recv_t.join(timeout=2.0)
        writ_t.join(timeout=2.0)
        print("Stopped.")

if __name__ == "__main__":
    main()
