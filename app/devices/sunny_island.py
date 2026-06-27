from devices.base import SmaDevice, power_sensor


class SunnyIsland(SmaDevice):
    """SMA Sunny Island battery inverter.

    Matched by serial number only (set BATTERY_SERIAL in the .env).
    """

    role = "battery"
    name = "Battery Power"

    def handle(self, telegram):
        # Battery power: the sign indicates charge vs. discharge. Adjust once
        # real telegrams are seen.
        return [("battery/power_w", telegram.net_active_power_w())]

    def ha_sensors(self):
        return [power_sensor("sma_battery_w", "Battery Power", "battery/power_w")]
