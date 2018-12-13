from sc2 import BotAI
from sc2.constants import UnitTypeId, AbilityId
from sc2.unit import Unit
from sc2.units import Units
from typing import Union

import src.bot_logger as bot_logger
from src.bot_actions import is_researching
from src.helpers import roundrobin

COMBAT_UNIT_TYPES = [
    UnitTypeId.ZERGLING,
    UnitTypeId.BANELING,
    UnitTypeId.MUTALISK,
    UnitTypeId.ROACH,
    UnitTypeId.HYDRALISK,
    UnitTypeId.BROODLORD,
    UnitTypeId.CORRUPTOR,
    UnitTypeId.LURKER
]

ZERG_MELEE_WEAPON_UPGRADES = [
    AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL1,
    AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL2,
    AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL3
]

ZERG_RANGED_WEAPON_UPGRADES = [
    AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL1,
    AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL2,
    AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL3
]

ZERG_GROUND_ARMOR_UPGRADES = [
    AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL1,
    AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL2,
    AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL3
]

ZERG_FLYING_WEAPON_UPGRADES = [
    AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL1,
    AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL2,
    AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL3
]

ZERG_FLYING_ARMOR_UPGRADES = [
    AbilityId.RESEARCH_ZERGFLYERARMORLEVEL1,
    AbilityId.RESEARCH_ZERGFLYERARMORLEVEL2,
    AbilityId.RESEARCH_ZERGFLYERARMORLEVEL3
]

ULTRALISK_DEN_ABILITIES = [
    AbilityId.RESEARCH_CHITINOUSPLATING
]


def get_random_larva(bot: BotAI) -> Union[Unit, None]:
    larva = bot.units(UnitTypeId.LARVA).ready
    return larva.exists and larva.random


async def build_drone(bot: BotAI, larva=None):
    unit = larva if larva else get_random_larva(bot)
    if unit:
        bot_logger.log_action(bot, "building drone")
        return await bot.do(unit.train(UnitTypeId.DRONE))


async def build_zergling(bot: BotAI, larva):
    unit = larva if larva else get_random_larva(bot)
    if unit and bot.can_afford(UnitTypeId.ZERGLING) and bot.units(UnitTypeId.SPAWNINGPOOL).ready.exists and bot.supply_left > 2:
        bot_logger.log_action(bot, "building zergling")
        return await bot.do(unit.train(UnitTypeId.ZERGLING))


async def build_overlord(bot: BotAI, larva):
    if bot.can_afford(UnitTypeId.OVERLORD):
        unit = larva if larva else get_random_larva(bot)
        if unit:
            bot_logger.log_action(bot, "building overlord")
            return await bot.do(unit.train(UnitTypeId.OVERLORD))


async def upgrade_zergling_speed(bot: BotAI):
    spawning_pool = bot.units(UnitTypeId.SPAWNINGPOOL).ready
    if not spawning_pool.exists:
        return False
    spawning_pool = spawning_pool.first
    metabolic_boost = AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST
    if bot.can_afford(metabolic_boost):
        available_abilities = await bot.get_available_abilities(spawning_pool)
        if metabolic_boost in available_abilities:
            bot_logger.log_action(bot, 'upgrading metabolic boost')
            await bot.do(spawning_pool(metabolic_boost))
            return True
    return False


def get_forces(bot: BotAI) -> Units:
    return bot.units.of_type(COMBAT_UNIT_TYPES)


def geyser_has_extractor(bot: BotAI, geyser: Unit, distance: Union[int, float]=1.0):
    return bot.units(UnitTypeId.EXTRACTOR).closer_than(distance, geyser)


def is_already_researching_lair(bot: BotAI, building: Unit) -> bool:
    return is_researching(bot, building, AbilityId.UPGRADETOLAIR_LAIR)


def already_researching_lair(bot: BotAI) -> bool:
    return sum(
        [is_already_researching_lair(bot, hatch) for hatch in bot.units(UnitTypeId.HATCHERY)]) > 1


def is_already_researching_hive(bot: BotAI, building: Unit) -> bool:
    return is_researching(bot, building, AbilityId.UPGRADETOHIVE_HIVE)


def already_researching_hive(bot: BotAI) -> bool:
    return sum(
        [is_already_researching_hive(bot, lair)
         for lair in bot.units(UnitTypeId.LAIR)]
    ) > 1
