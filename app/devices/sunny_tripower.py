from devices.base import SmaDevice, power_sensor


class SunnyTripower(SmaDevice):
    """SMA Sunny Tripower PV inverter.

    Matched by serial number only (set PV_SERIAL in the .env).
    """

    role = "pv"
    name = "PV Power"

    def handle(self, telegram):
        # PV generation. If the value comes out with the wrong sign once real
        # telegrams are seen, flip it here.
        return [("pv/power_w", telegram.net_active_power_w())]

    def ha_sensors(self):
        return [power_sensor("sma_pv_w", "PV Power", "pv/power_w")]
