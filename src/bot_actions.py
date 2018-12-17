import math
from sc2 import BotAI, AbilityId, UnitTypeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from typing import Union, Optional, List, Callable

import src.bot_logger as bot_logger
from src.types import Location, UnitPredicate


async def build_building_once(bot: BotAI, building: UnitTypeId, location: Union[Point2, Point3, Unit], max_distance: int=20, unit: Optional[Unit]=None, random_alternative: bool=True, placement_step: int=2):
    if not bot.units(building).ready.exists and not bot.already_pending(building) and bot.can_afford(building):
        bot_logger.log_action(
            bot, "building {} at {}".format(building, location))
        return await bot.build(building, near=location, max_distance=max_distance, unit=unit, random_alternative=random_alternative, placement_step=placement_step)


def get_workers_per_townhall(bot: BotAI) -> int:
    """Returns the ratio between townhalls and workers if there are any townhalls"""
    return bot.workers.amount / \
        bot.townhalls.amount if bot.townhalls.ready.exists else bot.workers.ready.amount


def get_enemies_near_position(bot: BotAI, position: Location, distance: Union[int, float]=20, unit_filter: UnitPredicate=lambda u: u.can_attack_ground) -> Units:
    """Returns units closer than the distance from the given position."""
    enemies_close_by = bot.known_enemy_units.closer_than(distance, position)
    return enemies_close_by.filter(unit_filter)


def targettable_by_both(unit: Unit) -> bool:
    return True


def targettable_by_air_weapons(unit: Unit) -> bool:
    return unit.is_flying


def targettable_by_ground_weapons(unit: Unit) -> bool:
    return not unit.is_flying


def targettable_by_none(unit: Unit) -> bool:
    return False


def get_is_targettable_callable(unit: Unit) -> UnitPredicate:
    can_attack_air = unit.can_attack_air
    can_attack_ground = unit.can_attack_ground

    if can_attack_air and can_attack_ground:
        return targettable_by_both
    elif can_attack_air and not can_attack_ground:
        return targettable_by_air_weapons
    elif can_attack_ground:
        return targettable_by_ground_weapons
    else:
        return targettable_by_none


def is_threat_to_air(unit: Unit) -> bool:
    return unit.can_attack_air


def is_threat_to_ground(unit: Unit) -> bool:
    return unit.can_attack_ground


def get_is_threat_callable(unit: Unit) -> UnitPredicate:
    is_air_unit = unit.is_flying
    if is_air_unit:
        return is_threat_to_air
    else:
        return is_threat_to_ground


def is_researching(bot: BotAI, building: Unit, ability_id: AbilityId) -> bool:
    """Returns whether the given ability_id is in the orders of the """
    return sum([order.ability.id == ability_id for order in building.orders]) >= 1


def find_potential_enemy_expansions(bot: BotAI) -> List[Point2]:
    """Returns the potential locations of enemy expansions"""
    expansion_locations = []
    for point, _ in bot.expansion_locations.items():
        distance_to_enemy_start = point.distance_to(
            bot.enemy_start_locations[0])
        distance_to_own_start = point.distance_to(bot.start_location)
        if distance_to_enemy_start < distance_to_own_start:
            expansion_locations.append(point)
    return expansion_locations


def get_closest_to(locations: List[Location], Location) -> Location:
    closest_location = None
    closest_distance = math.inf
    for location in locations:
        distance_to_start = location.distance_to(
            location)
        if distance_to_start < closest_distance:
            closest_distance = distance_to_start
            closest_location = location
    return closest_location
