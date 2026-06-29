import speedwire
from devices.base import SmaDevice, power_sensor, energy_sensor

# SUSY ids that act as a grid energy meter:
#   270 = SMA Energy Meter, 372 = Sunny Home Manager 2.0
GRID_METER_SUSY_IDS = {270, 372}


class EnergyMeter(SmaDevice):
    """SMA Energy Meter / Sunny Home Manager (grid connection point)."""

    role = "grid"
    name = "Grid Power"

    def matches(self, telegram):
        if super().matches(telegram):
            return True
        # Auto-detect the grid meter by its SUSY id when no serial is configured.
        return self.serial is None and telegram.susy_id in GRID_METER_SUSY_IDS

    def handle(self, telegram):
        # Net active power (positive = grid draw, negative = feed-in) plus the
        # cumulative import/export counters for the HA Energy Dashboard.
        return [
            ("grid/power_w", telegram.net_active_power_w()),
            ("grid/energy_import_kwh", telegram.energy_kwh(speedwire.OBIS_E_PLUS)),
            ("grid/energy_export_kwh", telegram.energy_kwh(speedwire.OBIS_E_MINUS)),
        ]

    def ha_sensors(self):
        return [
            power_sensor("sma_grid_w", "Grid Power", "grid/power_w"),
            energy_sensor("sma_grid_import_kwh", "Grid Energy Import", "grid/energy_import_kwh"),
            energy_sensor("sma_grid_export_kwh", "Grid Energy Export", "grid/energy_export_kwh"),
        ]
