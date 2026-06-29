from devices.base import (
    PolledInverter, power_sensor, battery_sensor, energy_sensor,
)


class SunnyIsland(PolledInverter):
    """SMA Sunny Island battery inverter, polled via Speedwire Data2+ (BATTERY_IP)."""

    role = "battery"
    name = "Battery Power"

    def read(self, client):
        # AC power of the battery inverter (sign = charge vs. discharge; flip
        # here if needed), the state of charge, and the lifetime charge/discharge
        # energy counters for the Home Assistant Energy Dashboard.
        charged_kwh, discharged_kwh = client.battery_energy_kwh()
        return [
            ("battery/power_w", client.ac_power_w()),
            ("battery/soc_pct", client.battery_soc_pct()),
            ("battery/energy_in_kwh", charged_kwh),
            ("battery/energy_out_kwh", discharged_kwh),
        ]

    def ha_sensors(self):
        return [
            power_sensor("sma_battery_w", "Battery Power", "battery/power_w"),
            battery_sensor("sma_battery_soc", "Battery SoC", "battery/soc_pct"),
            energy_sensor("sma_battery_in_kwh", "Battery Energy In", "battery/energy_in_kwh"),
            energy_sensor("sma_battery_out_kwh", "Battery Energy Out", "battery/energy_out_kwh"),
        ]
