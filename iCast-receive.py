import socket
import json
import os
import tempfile

HOST = ''  # Symbolic name meaning all available interfaces
PORT = 50078  # The port to listen on
OUTPUT_FILENAME = "match-facts.json"

print(f"Starting UDP server on port {PORT}...")

def extract_penalty_time(field: str) -> str | None:
    """
    Extracts just the penalty time from a 'playernumber penalty_time' string.
    Returns None if the field is empty or invalid.
    """
    if not field:
        return None
    parts = field.strip().split()
    if len(parts) < 2:
        return None  # no penalty time present
    return parts[-1]  # last token is the time


def format_period_label(time_type: str , time: str, period: str) -> str:
    """
    Map the incoming period field to '1/3', '2/3', '3/3', or 'OT'.
    Accepts common variants like '1','2','3','4','OT','Overtime', etc.
    """
    
    if time_type == "GAME TIME":
        if period is None:
            return ""
        token = period.strip().lower()
        # Direct known forms
        if token in {"1", "p1", "period1", "first"}:
            return time + "\xa0\xa0\xa01/3"
        if token in {"2", "p2", "period2", "second"}:
            return time + "\xa0\xa0\xa02/3"
        if token in {"3", "p3", "period3", "third"}:
            return time + "\xa0\xa0\xa03/3"
        if token in {"4", "ot", "overtime", "extra", "sudden death", "suddendeath"}:
            return time + "\xa0\xa0\xa0OT"

    elif time_type == "INTERMISSION":
        return time + " Pause"
    
    elif time_type == "TIME-OUT":
        return "Time Out"




def write_json_atomic(path: str, data: dict) -> None:
    """
    Write JSON atomically so readers never see a partial file.
    1) write to a temp file in the same directory
    2) flush + fsync
    3) os.replace() to final path (atomic on POSIX/Windows NTFS)
    """
    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"), indent=0)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        # Best-effort cleanup if something failed before replace().
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    s.bind((HOST, PORT))
    print("Server is listening...")





    while True:
        try:
            data, addr = s.recvfrom(1024)

            # The provided datagram has a custom encoding where each character
            # is represented by 4 bytes, with the actual character being the last one.
            # Example: 'H' is sent as b'\x00\x00\x00H'
            # We parse this by taking every 4th byte, starting from index 3.
            payload_bytes = data[3::4]
            message = payload_bytes.decode('ascii')

            print(f"Received {len(data)} bytes from {addr}. Parsed message: '{message}'")

            # --- Extract data and save to JSON ---
            fields = message.split(';')

            # The protocol specifies up to 21 fields, but we only need up to #13 for this task.
            if len(fields) >= 13:
                # Map fields to a dictionary based on the provided structure.
                # Indices are 0-based, so Field #1 is at index 0.

                period_label = format_period_label(fields[12], fields[0], fields[3])

                score = fields[1] + "\xa0:\xa0" + fields[2]
                # time_period = fields[0] + "\xa0\xa0\xa0"  + fields[3] + "/3"
                match_facts = {
                    "time": fields[0],
                    "score_home": fields[1],
                    "score_guest": fields[2],
                    "score" : score,
                    "period": fields[3],
                    "time_period": period_label,
                    "home_penalty_1": extract_penalty_time(fields[4]),
                    "home_penalty_2": extract_penalty_time(fields[5]),
                    "guest_penalty_1": extract_penalty_time(fields[6]),
                    "guest_penalty_2": extract_penalty_time(fields[7]),
                    "home_team_name": fields[10],
                    "guest_team_name": fields[11],
                    "time_type": fields[12],
                }

                # Write the dictionary to a JSON file, overwriting it each time.
                # with open(OUTPUT_FILENAME, 'w') as json_file:
                #     json.dump(match_facts, json_file, indent=4)
                # print(f"Successfully updated {OUTPUT_FILENAME}")
                write_json_atomic(OUTPUT_FILENAME, match_facts)
                print(f"OK from {addr[0]}:{addr[1]} -> {OUTPUT_FILENAME}")


            else:
                print(f"Received packet with {len(fields)} fields, expected at least 13. Skipping.")

        except (UnicodeDecodeError, IndexError) as e:
            # This error occurs if parsing fails after a successful receive.
            # 'addr' is guaranteed to be defined here.
            print(f"Received malformed packet from {addr}. Could not parse. Raw (hex): {data.hex()}. Error: {e}")
        except Exception as e:
            # This catches other errors, e.g., from s.recvfrom() itself.
            # 'addr' may not be defined, so we don't print it.
            print(f"An error occurred: {e}")
