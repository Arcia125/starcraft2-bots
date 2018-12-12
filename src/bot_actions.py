from sc2 import BotAI
from sc2.position import Point2, Point3
from sc2.unit import Unit
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


def has_enemies_nearby(bot: BotAI, position: Union[Unit, Point2, Point3], distance: Union[int, float]=20) -> bool:
    """Returns whether there are enemies within the distance of the position"""
    return bot.known_enemy_units.closer_than(distance, position)
