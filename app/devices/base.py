def power_sensor(unique_id, name, topic_suffix):
    """Build a Home Assistant power sensor definition."""
    return {
        "unique_id": unique_id,
        "name": name,
        "state_topic_suffix": topic_suffix,
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
    }


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
