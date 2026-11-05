"""Find all SMA Speedwire devices on the local network and print their IPs.

Sends the SMA multicast discovery probe and lists every device that answers,
with the IP address it actually uses on your LAN (taken from the reply's source
address). Use this to find the real Speedwire IP of your Sunny Tripower / Sunny
Island when the Sunny Portal only shows their internal WLAN-AP address.

To tell the inverters apart it logs in once to each of them and reads the
battery state of charge: only a battery inverter has one.

    python discover_speedwire.py [password] [user|installer]

No external dependencies. Run it on the same machine/segment as the sniffer.
The app also runs this search at startup while an inverter IP is missing.
"""

import socket
import struct
import sys
import time

from speedwire_data2 import Data2Client, Data2Error

MCAST_GRP = "239.12.255.254"
MCAST_PORT = 9522

# Well-known SMA discovery request; every Speedwire device replies to it.
PROBE = bytes.fromhex("534d4100000402a0ffffffff0000002000000000")

LISTEN_SECONDS = 5


def _meter_serial(data):
    """Serial from an energy-meter telegram (0x6069), or None for other packets."""
    if len(data) < 24 or struct.unpack_from(">H", data, 16)[0] != 0x6069:
        return None
    return struct.unpack_from(">I", data, 20)[0]


def scan():
    """Probe the network; return {ip: meter serial, or None for other devices}."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", MCAST_PORT))
        mreq = struct.pack(
            "4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton("0.0.0.0")
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 8)
        sock.sendto(PROBE, (MCAST_GRP, MCAST_PORT))

        sock.settimeout(1.0)
        devices = {}
        deadline = time.monotonic() + LISTEN_SECONDS
        while time.monotonic() < deadline:
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                continue
            # We also receive our own probe; that is not a device.
            if data == PROBE or data[:4] != b"SMA\x00":
                continue
            devices[addr[0]] = devices.get(addr[0]) or _meter_serial(data)
        return devices
    finally:
        sock.close()


def describe_inverter(ip, password, user_group):
    """One report line for a device that is not an energy meter."""
    try:
        with Data2Client(ip, password, user_group) as client:
            has_battery = client.battery_soc_pct() is not None
            serial = client.serial
    except (Data2Error, OSError, ValueError) as exc:
        return f"  {ip}  type unknown: {exc}"

    if has_battery:
        return f"  {ip}  battery inverter  serial={serial}  -> battery_ip / BATTERY_IP"
    return f"  {ip}  PV inverter  serial={serial}  -> pv_ip / PV_IP"


def report(password="0000", user_group="user"):
    """Search for devices and print what was found. Never raises on network errors."""
    print("Searching for SMA devices on the network ...")
    try:
        devices = scan()
    except OSError as exc:
        print(f"SMA device search failed: {exc}")
        return

    if not devices:
        print("No SMA devices answered. Are you on the same network segment?")
        return

    print(f"Found {len(devices)} SMA device(s):")
    for ip in sorted(devices):
        if devices[ip]:
            print(f"  {ip}  energy meter  serial={devices[ip]}  (no IP setting needed)")
        else:
            print(describe_inverter(ip, password, user_group))


if __name__ == "__main__":
    report(*sys.argv[1:3])
