from sc2.unit import Unit
from sc2.units import Units
from sc2.client import Client
from sc2.position import Point2, Point3

from src.colors import DebugColor


class BotDebugger(object):
    def __init__(self):
        pass

    def draw_unit_range(self, client: Client, unit: Unit, color=DebugColor()):
        """Must be sent by send_debug"""
        unit_range = max(unit.ground_range, unit.air_range) + unit.radius
        client.debug_sphere_out(unit, unit_range, color=color)

    def draw_units_ranges(self, client: Client, units: Units, color=DebugColor()):
        """Must be sent by send_debug"""
        for unit in units:
            self.draw_unit_range(client, unit, color=color)

    def draw_unit_target(self, client: Client, unit: Unit, potential_targets: Units, color=DebugColor()):
        """Must be sent by send_debug"""
        unit_target = unit.order_target
        if unit_target:
            if isinstance(unit_target, int):
                unit_target = potential_targets.find_by_tag(unit_target)
                if unit_target:
                    client.debug_line_out(unit, unit_target, color=color)
            else:
                point2 = Point3((*unit_target, unit.position3d.z))
                client.debug_line_out(unit, point2, color=color)

    def draw_units_targets(self, client: Client, units: Units, potential_targets: Units, color=DebugColor()):
        """Must be sent by send_debug"""
        for unit in units:
            self.draw_unit_target(
                client, unit, potential_targets, color=color)

    async def send_debug(self, client: Client):
        return await client.send_debug()
