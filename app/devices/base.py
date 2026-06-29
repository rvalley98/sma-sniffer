def sensor(unique_id, name, topic_suffix, unit, device_class,
           state_class="measurement"):
    """Build a generic Home Assistant sensor definition."""
    return {
        "unique_id": unique_id,
        "name": name,
        "state_topic_suffix": topic_suffix,
        "unit_of_measurement": unit,
        "device_class": device_class,
        "state_class": state_class,
    }


def power_sensor(unique_id, name, topic_suffix):
    """Build a Home Assistant power sensor definition (W)."""
    return sensor(unique_id, name, topic_suffix, "W", "power")


def battery_sensor(unique_id, name, topic_suffix):
    """Build a Home Assistant battery state-of-charge sensor definition (%)."""
    return sensor(unique_id, name, topic_suffix, "%", "battery")


def energy_sensor(unique_id, name, topic_suffix):
    """Build a cumulative energy sensor (kWh) for the HA Energy Dashboard."""
    return sensor(
        unique_id, name, topic_suffix, "kWh", "energy",
        state_class="total_increasing",
    )


class SmaDevice:
    """Base class for an SMA device that emits Speedwire energy-meter telegrams."""

    role = "device"
    name = "SMA Device"

    def __init__(self, serial=None):
        self.serial = serial

    def matches(self, telegram):
        """Whether this device should handle the given telegram."""
        return self.serial is not None and telegram.serial == self.serial

    def handle(self, telegram):
        """Return a list of (topic_suffix, value) tuples to publish."""
        raise NotImplementedError

    def ha_sensors(self):
        """Return a list of Home Assistant sensor definitions."""
        return []


class PolledInverter:
    """Base class for an SMA inverter that is actively polled by IP.

    Inverters (Sunny Tripower, Sunny Island) do not broadcast their power, so
    they are queried over the Speedwire Data2+ protocol instead of matched
    against multicast telegrams.
    """

    role = "inverter"
    name = "SMA Inverter"

    def __init__(self, ip, serial=None, password="0000", user_group="user"):
        self.ip = ip
        self.serial = serial
        self.password = password
        self.user_group = user_group

    def read(self, client):
        """Query the given Data2Client; return (topic_suffix, value) tuples."""
        raise NotImplementedError

    def ha_sensors(self):
        """Return a list of Home Assistant sensor definitions."""
        return []
