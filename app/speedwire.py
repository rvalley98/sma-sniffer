import struct

# Protocol id of the SMA Energy Meter / Sunny Home Manager telegram (offset 16).
SMA_PROTOCOL_ENERGY_METER = 0x6069

# OBIS channels (4-byte instantaneous values, raw value is in 0.1 W).
OBIS_P_PLUS = 0x00010400   # active power drawn from grid (consumption)
OBIS_P_MINUS = 0x00020400  # active power fed into grid (export)

OBIS_END = 0x00000000
POWER_DIVISOR = 10.0

# Human-readable labels for known OBIS channels (used by the debug dump).
# Key: identifier -> (name, unit, scale); human value = raw * scale.
OBIS_LABELS = {
    0x00010400: ("P+ active power import", "W", 0.1),
    0x00020400: ("P- active power export", "W", 0.1),
    0x00030400: ("Q+ reactive power import", "var", 0.1),
    0x00040400: ("Q- reactive power export", "var", 0.1),
    0x00090400: ("S+ apparent power import", "VA", 0.1),
    0x000A0400: ("S- apparent power export", "VA", 0.1),
    0x000D0400: ("power factor", "", 0.001),
    0x000E0400: ("frequency", "Hz", 0.001),
    0x00150400: ("L1 P+ import", "W", 0.1),
    0x00160400: ("L1 P- export", "W", 0.1),
    0x001F0400: ("L1 current", "A", 0.001),
    0x00200400: ("L1 voltage", "V", 0.001),
    0x00290400: ("L2 P+ import", "W", 0.1),
    0x002A0400: ("L2 P- export", "W", 0.1),
    0x00330400: ("L2 current", "A", 0.001),
    0x00340400: ("L2 voltage", "V", 0.001),
    0x003D0400: ("L3 P+ import", "W", 0.1),
    0x003E0400: ("L3 P- export", "W", 0.1),
    0x00470400: ("L3 current", "A", 0.001),
    0x00480400: ("L3 voltage", "V", 0.001),
}


class Telegram:
    """A decoded SMA Speedwire energy-meter telegram."""

    def __init__(self, susy_id: int, serial: int, obis: dict):
        self.susy_id = susy_id
        self.serial = serial
        self.obis = obis

    def power_w(self, obis_code: int):
        """Single OBIS channel value in watts (or None if not present)."""
        value = self.obis.get(obis_code)
        return None if value is None else value / POWER_DIVISOR

    def net_active_power_w(self):
        """Net active power: positive = import/draw, negative = export/feed-in."""
        p_plus = self.obis.get(OBIS_P_PLUS)
        p_minus = self.obis.get(OBIS_P_MINUS)
        if p_plus is None and p_minus is None:
            return None
        return round(((p_plus or 0) - (p_minus or 0)) / POWER_DIVISOR, 1)

    def describe(self):
        """Human-readable lines for every decoded OBIS channel (for debugging)."""
        lines = []
        for code in sorted(self.obis):
            raw = self.obis[code]
            label, unit, scale = OBIS_LABELS.get(code, (None, "", None))
            if label is None:
                lines.append(f"  {code:#010x} = {raw} (raw, unknown)")
            else:
                lines.append(
                    f"  {code:#010x} {label}: {raw * scale:g} {unit}".rstrip()
                )
        return lines


def _obis_channel_len(identifier: int) -> int:
    """Length of an OBIS channel's data in bytes.

    The second byte of the identifier encodes the measurement type:
    0x04 = instantaneous value (4 bytes), 0x08 = counter (8 bytes).
    """
    type_byte = (identifier >> 8) & 0xFF
    return 8 if type_byte == 0x08 else 4


def parse(data: bytes):
    """Parse an SMA Energy Meter / Home Manager Speedwire telegram.

    Returns a Telegram, or None if the packet is not a 0x6069 telegram.
    """
    if len(data) < 28 or data[:4] != b"SMA\x00":
        return None

    protocol = struct.unpack_from(">H", data, 16)[0]
    if protocol != SMA_PROTOCOL_ENERGY_METER:
        return None

    susy_id = struct.unpack_from(">H", data, 18)[0]
    serial = struct.unpack_from(">I", data, 20)[0]

    obis = {}
    pos = 28
    n = len(data)

    while pos + 4 <= n:
        identifier = struct.unpack_from(">I", data, pos)[0]
        if identifier == OBIS_END:
            break

        clen = _obis_channel_len(identifier)
        pos += 4
        if pos + clen > n:
            break

        if clen == 8:
            value = struct.unpack_from(">Q", data, pos)[0]
        else:
            value = struct.unpack_from(">I", data, pos)[0]

        obis[identifier] = value
        pos += clen

    return Telegram(susy_id, serial, obis)
