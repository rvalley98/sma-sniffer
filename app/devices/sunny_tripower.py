from devices.base import PolledInverter, power_sensor


class SunnyTripower(PolledInverter):
    """SMA Sunny Tripower PV inverter, polled via Speedwire Data2+ (PV_IP)."""

    role = "pv"
    name = "PV Power"

    def read(self, client):
        # Total AC power of the PV inverter. If the sign is wrong for your
        # setup once real values are seen, negate it here.
        return [("pv/power_w", client.ac_power_w())]

    def ha_sensors(self):
        return [power_sensor("sma_pv_w", "PV Power", "pv/power_w")]
