from devices.base import PolledInverter, power_sensor, energy_sensor


class SunnyTripower(PolledInverter):
    """SMA Sunny Tripower PV inverter, polled via Speedwire Data2+ (PV_IP)."""

    role = "pv"
    name = "PV Power"

    def read(self, client):
        # Total AC power of the PV inverter. If the sign is wrong for your
        # setup once real values are seen, negate it here.
        total_kwh, today_kwh = client.yield_counters_kwh()
        return [
            ("pv/power_w", client.ac_power_w()),
            ("pv/energy_total_kwh", total_kwh),
            ("pv/energy_today_kwh", today_kwh),
        ]

    def ha_sensors(self):
        return [
            power_sensor("sma_pv_w", "PV Power", "pv/power_w"),
            energy_sensor("sma_pv_total_kwh", "PV Energy Total", "pv/energy_total_kwh"),
            energy_sensor("sma_pv_today_kwh", "PV Energy Today", "pv/energy_today_kwh"),
        ]
