import socket
import time

# Import the payloads from your external file.
# Note: I'm assuming the filename is 'udp_payloads.py'.
# Make sure this file is in the same directory or in your PYTHONPATH.
from udp_payloads import payloads

# The server's port
PORT = 50078
# The global broadcast address
BROADCAST_ADDR = "255.255.255.255"

# --- Main execution ---
# Create a UDP socket
# Use a 'with' statement for automatic cleanup
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
    # Set the socket option to allow broadcasting
    # This is necessary on many systems to send to a broadcast address
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print(f"Continuously sending {len(payloads)} packets to {BROADCAST_ADDR}:{PORT}...")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            # Loop through all the captured payloads
            for i, payload in enumerate(payloads):
                client_socket.sendto(payload, (BROADCAST_ADDR, PORT))
                # Use end='\r' to update the line in place
                print(f"Sent packet {i + 1}/{len(payloads)}", end='\r')
                time.sleep(0.1)  # Small delay to simulate the stream
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
