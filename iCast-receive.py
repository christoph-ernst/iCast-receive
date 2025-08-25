import socket
import json

HOST = ''  # Symbolic name meaning all available interfaces
PORT = 50078  # The port to listen on
OUTPUT_FILENAME = "match-facts.json"

print(f"Starting UDP server on port {PORT}...")

# Create a UDP socket using a 'with' statement for automatic cleanup
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    # Allow reusing a local address, helpful for quick server restarts
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Allow receiving broadcast packets. This must be set before binding.
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Bind the socket to the host and port
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
                score = fields[1] + "\xa0:\xa0" + fields[2]
                time_period = fields[0] + "\xa0\xa0\xa0"  + fields[3] + "/3"
                match_facts = {
                    "time": fields[0],
                    "score_home": fields[1],
                    "score_guest": fields[2],
                    "score" : score,
                    "period": fields[3],
                    "time_period": time_period,
                    "home_penalty_1": fields[4],
                    "home_penalty_2": fields[5],
                    "guest_penalty_1": fields[6],
                    "guest_penalty_2": fields[7],
                    "home_team_name": fields[10],
                    "guest_team_name": fields[11],
                    "time_type": fields[12],
                }

                # Write the dictionary to a JSON file, overwriting it each time.
                with open(OUTPUT_FILENAME, 'w') as json_file:
                    json.dump(match_facts, json_file, indent=4)
                print(f"Successfully updated {OUTPUT_FILENAME}")
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
