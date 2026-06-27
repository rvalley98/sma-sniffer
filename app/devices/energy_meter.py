from devices.base import SmaDevice, power_sensor

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
        # Net active power: positive = grid draw, negative = feed-in.
        return [("grid/power_w", telegram.net_active_power_w())]

    def ha_sensors(self):
        return [power_sensor("sma_grid_w", "Grid Power", "grid/power_w")]
