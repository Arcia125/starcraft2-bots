from sc2 import BotAI, AbilityId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from typing import Union

import src.bot_logger as bot_logger


async def build_building_once(bot: BotAI, building, location):
    if not bot.units(building).ready.exists and not bot.already_pending(building) and bot.can_afford(building):
        bot_logger.log_action(
            bot, "building {} at {}".format(building, location))
        return await bot.build(building, near=location)


def get_workers_per_townhall(bot: BotAI) -> int:
    """Returns the ratio between townhalls and workers if there are any townhalls"""
    return bot.workers.amount / \
        bot.townhalls.amount if bot.townhalls.ready.exists else bot.workers.ready.amount


def get_enemies_near_position(bot: BotAI, position: Union[Unit, Point2, Point3], distance: Union[int, float]=20, unit_filter=lambda u: u.can_attack_ground) -> Units:
    """Returns units closer than the distance from the given position."""
    enemies_close_by = bot.known_enemy_units.closer_than(distance, position)
    return enemies_close_by.filter(unit_filter)


def is_researching(bot: BotAI, building: Unit, ability_id: AbilityId) -> bool:
    """Returns whether the given ability_id is in the orders of the """
    return sum([order.ability.id == ability_id for order in building.orders]) > 1
