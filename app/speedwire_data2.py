"""Client for the SMA Speedwire "Data2+" inverter protocol (UDP port 9522).

Unlike the SMA Energy Meter, inverters (Sunny Tripower, Sunny Island, ...) do
*not* broadcast their measurements. They have to be queried directly by IP: log
in with the device password, then request individual "spot value" registers.

The wire format below was reconstructed from the FHEM ``76_SMAInverter`` module
and SBFspot. Layout of a packet::

    offset
    0    "SMA\\0"                              ┐ outer Speedwire header
    4    00 04 02 A0   tag0 (len 4 / id 02A0)  │
    8    00 00 00 01   group = 1               │
    12   <data length> (2 bytes, big-endian)   │ = len(frame after esignature)
    14   00 10         SMA Net 2 tag           │
    16   60 65         protocol id 0x6065      │
    18   <longwords> <ctrl=0xA0>               ┘
    20   dst SusyID (2) + dst Serial (4)       ┐ inner SMA Net 2 frame,
    26   control (2)                           │ everything little-endian
    28   src SusyID (2) + src Serial (4)       │
    34   control (2)                           │
    36   status/error (2) + fragment (2)       │
    40   packet id (2, with 0x8000 bit)        │
    42   command (4) + first reg (4) + ...     ┘

Responses mirror that header; the *source* of the reply (offset 28/30) is the
inverter, and spot values start at offset 62 with a 28-byte record stride.
"""

import socket
import struct
import time

DEFAULT_PORT = 9522

# Constant prefix: "SMA\0" + tag0 (len 4 / id 0x02A0) + group 1. The 2-byte
# data-length field and the SMA-Net-2 / protocol bytes are appended per packet.
_HEADER = bytes.fromhex("534D4100000402A000000001")
_NET2_PROTOCOL = bytes.fromhex("00106065")  # SMA Net 2 tag (0x0010) + 0x6065

# Control byte of the inner frame and the "longwords" count per packet type.
_CTRL = 0xA0
_LONGWORDS_LOGIN = 0x0E
_LONGWORDS_QUERY = 0x09
_LONGWORDS_LOGOFF = 0x08

# Commands.
_CMD_LOGIN = 0xFFFD040C
_CMD_LOGOFF = 0xFFFD010E

# User groups: (login code, password-encoding byte).
_USER_GROUPS = {
    "user": (0x07, 0x88),
    "installer": (0x0A, 0xBB),
}

# Login timeout the inverter keeps the session open for (seconds).
_SESSION_TIMEOUT = 0x00000384  # 900

# Broadcast destination used before the inverter's real address is known.
_DST_SUSY_ANY = 0xFFFF
_DST_SERIAL_ANY = 0xFFFFFFFF

# This client's own (arbitrary) address; the inverter just echoes it back.
# These are the values SBFspot uses (SusyID 125, a serial in 900000000+).
_SRC_SUSY = 0x007D
_SRC_SERIAL = 0x3A289B7C

# Control word (ctrl2), little-endian, per packet type.
_CTRL2_LOGIN = 0x0100
_CTRL2_LOGOFF = 0x0300
_CTRL2_QUERY = 0x0000

# Discovery request: makes the inverter reveal its real SusyID/Serial.
_CMD_DISCOVER = (0x00000200, 0x00000000, 0x00000000)

# Spot value registers: (command, first, last).
_REG_AC_POWER = (0x51000200, 0x00263F00, 0x00263FFF)   # total AC power (Pac), W
_REG_BATTERY_SOC = (0x51000200, 0x00295A00, 0x00295AFF)  # battery charge, %

# Markers the inverter uses for "value not available".
_NAN_UNSIGNED = 0xFFFFFFFF
_NAN_SIGNED = 0x80000000

# Spot values sit at offset 62, then every 28 bytes for multi-value responses.
_VALUE_OFFSET = 62
_RECORD_STRIDE = 28


class Data2Error(Exception):
    """Raised when the inverter cannot be reached or the login is rejected."""


class Data2Client:
    """Talks to a single SMA inverter over Speedwire Data2+.

    Use as a context manager so login/logoff and the socket are handled::

        with Data2Client("192.168.0.172", password="0000") as inv:
            power = inv.ac_power_w()
            soc = inv.battery_soc_pct()
    """

    def __init__(self, ip, password="0000", user_group="user",
                 port=DEFAULT_PORT, timeout=5.0, debug=False):
        self.ip = ip
        self.password = password
        self.user_group = user_group.strip().lower()
        if self.user_group not in _USER_GROUPS:
            raise ValueError(f"Unknown user group '{user_group}'")
        self.port = port
        self.timeout = timeout
        self.debug = debug

        self._sock = None
        self._pktid = 0
        # Inverter address, learned from the login reply.
        self._dst_susy = _DST_SUSY_ANY
        self._dst_serial = _DST_SERIAL_ANY

    @property
    def serial(self):
        """The inverter's serial, once learned from discovery/login."""
        return None if self._dst_serial == _DST_SERIAL_ANY else self._dst_serial

    @property
    def susy_id(self):
        """The inverter's SusyID, once learned from discovery/login."""
        return None if self._dst_susy == _DST_SUSY_ANY else self._dst_susy

    # -- context manager ---------------------------------------------------

    def __enter__(self):
        self.connect()
        self.discover()
        self.login()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.logoff()
        except OSError:
            pass
        self.close()
        return False

    # -- connection --------------------------------------------------------

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(self.timeout)
        # connect() pins the peer so recv() only accepts the inverter's replies.
        sock.connect((self.ip, self.port))
        self._sock = sock

    def close(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    # -- packet construction ----------------------------------------------

    def _next_pktid(self):
        self._pktid = (self._pktid + 1) & 0x7FFF
        return self._pktid

    def _build(self, longwords, control_word, body_payload):
        """Wrap an inner-frame payload in the full Speedwire envelope.

        ``body_payload`` is everything after the packet-id field (command, ...).
        ``control_word`` is the 2-byte control value used in both control slots
        (0x0100 for login, 0x0000 for queries, 0x0300 for logoff).
        """
        pktid = self._next_pktid()
        frame = b"".join((
            struct.pack("<H", self._dst_susy),
            struct.pack("<I", self._dst_serial),
            struct.pack("<H", control_word),
            struct.pack("<H", _SRC_SUSY),
            struct.pack("<I", _SRC_SERIAL),
            struct.pack("<H", control_word),
            b"\x00\x00\x00\x00",                 # status + fragment
            struct.pack("<H", 0x8000 | pktid),   # packet id
            body_payload,
        ))
        esignature = _NET2_PROTOCOL + bytes((longwords, _CTRL))
        packet = (
            _HEADER + struct.pack(">H", len(frame)) + esignature + frame
        )
        return packet, pktid

    def _login_packet(self):
        group_code, enc_byte = _USER_GROUPS[self.user_group]
        encoded = bytes(
            (enc_byte + (ord(self.password[i]) if i < len(self.password) else 0))
            & 0xFF
            for i in range(12)
        )
        body = b"".join((
            struct.pack("<I", _CMD_LOGIN),
            struct.pack("<I", group_code),
            struct.pack("<I", _SESSION_TIMEOUT),
            struct.pack("<I", int(time.time()) & 0xFFFFFFFF),
            b"\x00\x00\x00\x00",
            encoded,
            b"\x00\x00\x00\x00",
        ))
        return self._build(_LONGWORDS_LOGIN, _CTRL2_LOGIN, body)

    def _logoff_packet(self):
        body = (
            struct.pack("<I", _CMD_LOGOFF)
            + struct.pack("<I", 0xFFFFFFFF)
            + b"\x00\x00\x00\x00"
        )
        return self._build(_LONGWORDS_LOGOFF, _CTRL2_LOGOFF, body)

    def _query_packet(self, command, first, last):
        body = (
            struct.pack("<I", command)
            + struct.pack("<I", first)
            + struct.pack("<I", last)
            + b"\x00\x00\x00\x00"
        )
        return self._build(_LONGWORDS_QUERY, _CTRL2_QUERY, body)

    # -- transport ---------------------------------------------------------

    def _exchange(self, packet, want_pktid):
        """Send a packet and return the matching 0x6065 reply (or raise)."""
        if self.debug:
            print(f"[DATA2] -> {self.ip} {packet.hex()}")
        self._sock.send(packet)

        # Read replies until one matches our packet id (skip stray datagrams).
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                data = self._sock.recv(4096)
            except socket.timeout:
                break
            if self.debug:
                print(f"[DATA2] <- {self.ip} {data.hex()}")
            if len(data) < 42 or data[:4] != b"SMA\x00":
                continue
            if struct.unpack_from(">H", data, 16)[0] != 0x6065:
                continue
            if struct.unpack_from("<H", data, 40)[0] != (0x8000 | want_pktid):
                continue
            return data
        raise Data2Error(f"No reply from inverter {self.ip}")

    # -- high level --------------------------------------------------------

    def discover(self):
        """Learn the inverter's real SusyID/Serial (sent to the broadcast id)."""
        command, first, last = _CMD_DISCOVER
        packet, pktid = self._query_packet(command, first, last)
        data = self._exchange(packet, pktid)
        self._dst_susy = struct.unpack_from("<H", data, 28)[0]
        self._dst_serial = struct.unpack_from("<I", data, 30)[0]

    def login(self):
        packet, pktid = self._login_packet()
        data = self._exchange(packet, pktid)
        # The reply's *source* address (offset 28/30) is the real inverter.
        self._dst_susy = struct.unpack_from("<H", data, 28)[0]
        self._dst_serial = struct.unpack_from("<I", data, 30)[0]
        status = struct.unpack_from("<H", data, 36)[0]
        if status != 0:
            raise Data2Error(
                f"Login to {self.ip} rejected (status=0x{status:04x}); "
                "check INVERTER_PASSWORD / INVERTER_USER_GROUP."
            )

    def logoff(self):
        if self._sock is None:
            return
        packet, _ = self._logoff_packet()
        # Logoff is fire-and-forget; the inverter does not always reply.
        if self.debug:
            print(f"[DATA2] -> {self.ip} (logoff) {packet.hex()}")
        self._sock.send(packet)

    def _read_value(self, register, signed=False):
        command, first, last = register
        packet, pktid = self._query_packet(command, first, last)
        data = self._exchange(packet, pktid)
        if len(data) < _VALUE_OFFSET + 4:
            return None
        raw = struct.unpack_from("<i" if signed else "<I", data, _VALUE_OFFSET)[0]
        if (raw & 0xFFFFFFFF) in (_NAN_UNSIGNED, _NAN_SIGNED):
            return None
        return raw

    def ac_power_w(self):
        """Total AC active power in watts (sign depends on the device)."""
        return self._read_value(_REG_AC_POWER, signed=True)

    def battery_soc_pct(self):
        """Battery state of charge in percent (Sunny Island), or None."""
        return self._read_value(_REG_BATTERY_SOC, signed=False)

    def query_raw(self, command, first, last):
        """Send one register query and return the raw reply bytes."""
        packet, pktid = self._query_packet(command, first, last)
        return self._exchange(packet, pktid)

    def read_counter_wh(self, register):
        """Read a 64-bit Wh counter (energy queries, 16-byte records)."""
        command, first, last = register
        data = self.query_raw(command, first, last)
        if len(data) < _VALUE_OFFSET + 8:
            return None
        raw = struct.unpack_from("<Q", data, _VALUE_OFFSET)[0]
        if raw in (0xFFFFFFFFFFFFFFFF, _NAN_SIGNED):
            return None
        return raw


def dump_records(data):
    """Yield (lri, class, timestamp, value32, value64) for each reply record.

    Records start at offset 54. Instantaneous values use a 28-byte stride and a
    32-bit value at +8; 64-bit counters (energy) use a 16-byte stride. We can't
    know the stride up front, so this yields both interpretations' values per
    16-byte step and lets the caller eyeball which register is which.
    """
    end = len(data) - 4  # drop the trailing 00000000
    pos = 54
    while pos + 12 <= end:
        code = struct.unpack_from("<I", data, pos)[0]
        lri = code & 0x00FFFF00
        cls = code & 0xFF
        timestamp = struct.unpack_from("<I", data, pos + 4)[0]
        value32 = struct.unpack_from("<i", data, pos + 8)[0]
        value64 = (
            struct.unpack_from("<q", data, pos + 8)[0]
            if pos + 16 <= len(data) else None
        )
        yield lri, cls, timestamp, value32, value64
        # Energy counters pack 64-bit values (16-byte records); spot values are
        # 28-byte. Step by the smaller stride so we never skip a record.
        pos += 16 if lri in (0x00260100, 0x00496700, 0x00492600) else 28


# Named register ranges for the CLI dump mode.
_DUMP_PRESETS = {
    "energy": (0x54000200, 0x00260100, 0x002622FF),   # metering Wh totals
    "batload": (0x54000200, 0x00496700, 0x004967FF),  # battery charge today/total
    "batdiag": (0x51000200, 0x00491E00, 0x00495DFF),  # battery V/A/temp/throughput
}


def _cli():
    """Quick test / register dump for an SMA inverter.

    python speedwire_data2.py <ip> [password] [user|installer]
    python speedwire_data2.py <ip> <password> <group> dump <energy|batload|batdiag>
    python speedwire_data2.py <ip> <password> <group> dump <cmdhex> <firsthex> <lasthex>
    """
    import sys

    if len(sys.argv) < 2:
        print(_cli.__doc__)
        return 1

    ip = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else "0000"
    group = sys.argv[3] if len(sys.argv) > 3 else "user"

    dump = None
    if len(sys.argv) > 4 and sys.argv[4] == "dump":
        if len(sys.argv) == 6 and sys.argv[5] in _DUMP_PRESETS:
            dump = _DUMP_PRESETS[sys.argv[5]]
        elif len(sys.argv) == 8:
            dump = tuple(int(x, 16) for x in sys.argv[5:8])
        else:
            print("dump needs a preset (energy|batload|batdiag) or cmd/first/last hex")
            return 1

    try:
        with Data2Client(ip, password, group, debug=True) as inv:
            print(f"Connected: SusyID={inv.susy_id} serial={inv.serial}")
            if dump is None:
                print(f"AC power : {inv.ac_power_w()} W")
                print(f"Battery SoC: {inv.battery_soc_pct()} %")
            else:
                data = inv.query_raw(*dump)
                print(f"--- records for {[hex(x) for x in dump]} ---")
                for lri, cls, ts, v32, v64 in dump_records(data):
                    print(
                        f"  lri=0x{lri:08x} cls={cls:#04x} "
                        f"val32={v32} val64={v64}"
                    )
    except Data2Error as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
