from sc2 import BotAI
from sc2.constants import AbilityId, PYLON, STALKER, ZEALOT, SENTRY, GATEWAY, ROBOTICSFACILITY, IMMORTAL, WARPGATE


async def build_proxy(bot: BotAI, distance_towards_location=1, towards_location=None):
    location = towards_location or bot.enemy_start_locations[0]
    p = bot.game_info.map_center.towards_with_random_angle(
        location, distance_towards_location)
    return await bot.build(PYLON, near=p)


async def micro_sentries(bot: BotAI):
    sentries = bot.units(SENTRY).ready
    actions = []
    for sentry in sentries:
        if bot.known_enemy_units.exists:
            closest_known_enemy = bot.known_enemy_units.closest_to(
                sentry.position)
            if sentry.target_in_range(closest_known_enemy):
                guardian_shield = AbilityId.GUARDIANSHIELD_GUARDIANSHIELD
                can_cast = await bot.can_cast(sentry, guardian_shield)
                if can_cast:
                    actions.append(sentry(guardian_shield))
            actions.append(sentry.attack(closest_known_enemy))
        else:
            target = bot.known_enemy_structures.random_or(
                bot.known_enemy_units.random_or(bot.enemy_start_locations[0]))
            actions.append(sentry.attack(target))
    await bot.do_actions(actions)


async def micro_zealots(bot: BotAI):
    zealots = bot.units(ZEALOT).ready
    actions = []
    for zealot in zealots:
        if bot.known_enemy_units.exists:
            actions.append(zealot.attack(
                bot.known_enemy_units.closest_to(zealot.position)))
        else:
            target = bot.known_enemy_structures.random_or(
                bot.known_enemy_units.random_or(bot.enemy_start_locations[0]))
            actions.append(zealot.attack(target))
    await bot.do_actions(actions)


async def micro_stalkers(bot: BotAI):
    stalkers = bot.units(STALKER).ready
    actions = []
    for stalker in stalkers:
        enemy_threats_close = bot.known_enemy_units.filter(
            lambda x: x.can_attack_ground).closer_than(15, stalker)  # threats that can attack
        if enemy_threats_close.exists:
            closest_enemy = enemy_threats_close.sorted_by_distance_to(
                stalker).first
            if stalker.weapon_cooldown == 0:
                actions.append(stalker.attack(closest_enemy))
            elif not bot.known_enemy_units.filter(
                    lambda x: x.can_attack_ground).closer_than(3, stalker).exists:
                actions.append(stalker.move(closest_enemy.position))
        else:
            target = bot.known_enemy_structures.random_or(
                bot.known_enemy_units.random_or(bot.enemy_start_locations[0]))
            actions.append(stalker.attack(target))
    await bot.do_actions(actions)


async def micro_immortals(bot: BotAI):
    immortals = bot.units(IMMORTAL).ready
    actions = []
    for immortal in immortals:
        enemy_threats_close = bot.known_enemy_units.filter(
            lambda x: x.can_attack_ground).closer_than(15, immortal)  # threats that can attack
        if enemy_threats_close.exists:
            closest_enemy = enemy_threats_close.sorted_by_distance_to(
                immortal).first
            if immortal.weapon_cooldown == 0:
                actions.append(immortal.attack(closest_enemy))
            elif not bot.known_enemy_units.filter(
                    lambda x: x.can_attack_ground).closer_than(5, immortal).exists:
                actions.append(immortal.move(closest_enemy.position))
        else:
            target = bot.known_enemy_structures.random_or(
                bot.known_enemy_units.random_or(bot.enemy_start_locations[0]))
            actions.append(immortal.attack(target))
    await bot.do_actions(actions)


async def chronoboost_building(bot: BotAI, nexus, building=None):
    if not building:
        building = bot.units(WARPGATE).ready.random_or(bot.units(GATEWAY).ready.random_or(
            bot.units(ROBOTICSFACILITY).ready.random_or(bot.townhalls.ready.random)))
    chronoboost = AbilityId.EFFECT_CHRONOBOOSTENERGYCOST
    await bot.do(nexus(chronoboost, building))


async def micro_army(bot: BotAI):
    await micro_zealots(bot)
    await micro_stalkers(bot)
    await micro_sentries(bot)
    await micro_immortals(bot)


def get_closest_pylon_to_enemy_base(bot: BotAI):
    proxy_pylon = bot.units(PYLON).closest_to(
        bot.enemy_start_locations[0])
    return proxy_pylon
