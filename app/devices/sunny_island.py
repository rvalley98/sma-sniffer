from devices.base import PolledInverter, power_sensor, battery_sensor


class SunnyIsland(PolledInverter):
    """SMA Sunny Island battery inverter, polled via Speedwire Data2+ (BATTERY_IP)."""

    role = "battery"
    name = "Battery Power"

    def read(self, client):
        # AC power of the battery inverter (sign = charge vs. discharge; flip
        # here if needed) plus the battery state of charge.
        return [
            ("battery/power_w", client.ac_power_w()),
            ("battery/soc_pct", client.battery_soc_pct()),
        ]

    def ha_sensors(self):
        return [
            power_sensor("sma_battery_w", "Battery Power", "battery/power_w"),
            battery_sensor("sma_battery_soc", "Battery SoC", "battery/soc_pct"),
        ]
