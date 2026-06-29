"""Find all SMA Speedwire devices on the local network and print their IPs.

Sends the SMA multicast discovery probe and lists every device that answers,
with the IP address it actually uses on your LAN (taken from the reply's source
address). Use this to find the real Speedwire IP of your Sunny Tripower / Sunny
Island when the Sunny Portal only shows their internal WLAN-AP address.

    python discover_speedwire.py

No external dependencies. Run it on the same machine/segment as the sniffer.
"""

import socket
import struct
import time

MCAST_GRP = "239.12.255.254"
MCAST_PORT = 9522

# Well-known SMA discovery request; every Speedwire device replies to it.
PROBE = bytes.fromhex("534d4100000402a0ffffffff0000002000000000")

LISTEN_SECONDS = 5


def _identity(data):
    """Best-effort (susy_id, serial) from a reply, or (None, None)."""
    if len(data) < 24 or data[:4] != b"SMA\x00":
        return None, None
    protocol = struct.unpack_from(">H", data, 16)[0]
    if protocol in (0x6069, 0x6065):
        # Energy-meter telegrams carry susy/serial big-endian at 18/20.
        susy = struct.unpack_from(">H", data, 18)[0]
        serial = struct.unpack_from(">I", data, 20)[0]
        return susy, serial
    return None, None


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", MCAST_PORT))
    mreq = struct.pack(
        "4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton("0.0.0.0")
    )
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 8)

    print(f"Sending Speedwire discovery to {MCAST_GRP}:{MCAST_PORT} ...")
    sock.sendto(PROBE, (MCAST_GRP, MCAST_PORT))

    sock.settimeout(1.0)
    devices = {}
    deadline = time.monotonic() + LISTEN_SECONDS
    while time.monotonic() < deadline:
        try:
            data, addr = sock.recvfrom(2048)
        except socket.timeout:
            continue
        ip = addr[0]
        susy, serial = _identity(data)
        # Keep the most informative reply seen per IP.
        if ip not in devices or (serial and not devices[ip][1]):
            devices[ip] = (susy, serial)

    print()
    if not devices:
        print("No SMA devices answered. Are you on the same network segment?")
        return

    print(f"Found {len(devices)} SMA device(s):")
    for ip in sorted(devices):
        susy, serial = devices[ip]
        extra = f"  susy={susy} serial={serial}" if serial else ""
        print(f"  {ip}{extra}")


if __name__ == "__main__":
    main()
