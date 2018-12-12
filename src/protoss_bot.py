import random
import sc2
from sc2.unit import Unit
from sc2.constants import AbilityId, BuffId, NEXUS, PROBE, PYLON, ASSIMILATOR, STALKER, ZEALOT, SENTRY, FORGE, GATEWAY, CYBERNETICSCORE, ROBOTICSFACILITY, IMMORTAL, TWILIGHTCOUNCIL, WARPGATE, PHOTONCANNON
from sc2.position import Point2, Point3

import src.bot_logger as bot_logger
from src.helpers import roundrobin
from src.protoss_actions import micro_army, chronoboost_building, build_proxy, get_closest_pylon_to_enemy_base


class BalancedProtossBot(sc2.BotAI):
    def __init__(self):
        self.attacking = False
        self.attack_count = 0
        self.warpgate_started = False
        self.warpgate_start_time = None
        self.warpgate_finished = False
        self.proxy_built = False
        self.zealot_charge_started = False
        self.booming = True
        self.boom_timings = [
            (0, 250),
            (300, 400),
            (500, 600),
            (800, 1000)
        ]

    @property
    def is_researching_warpgate(self):
        return self.warpgate_start_time and self.time - \
            self.warpgate_start_time < 120

    @property
    def is_booming(self):
        now = self.time
        return any(minimum < now < maximum for minimum, maximum in self.boom_timings)

    def manage_booming(self):
        if self.is_booming:
            if not self.booming:
                self.booming = True
        else:
            if self.booming:
                self.booming = False

    def on_start(self):
        self.attack_upgrades = [
            AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1,
            AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2,
            AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3
        ]

        self.armor_upgrades = [
            AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1,
            AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2,
            AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3
        ]

        self.shield_upgrades = [
            AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL1,
            AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL2,
            AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL3
        ]

        self.all_upgrades = roundrobin(
            self.attack_upgrades, self.armor_upgrades, self.shield_upgrades)

    async def first_iteration(self):
        await self.chat_send("(glhf)")
        await self.distribute_workers()
        await self.scout_enemy()

    async def on_step(self, iteration):
        if iteration == 0:
            await self.first_iteration()
        if iteration % 8 == 0:
            self.manage_booming()
        if iteration % 50 == 0:
            await self.position_army()
            await self.set_rally_points()
            await self.distribute_workers()
            if 600 < self.time < 610:
                await self.scout_enemy()
        if iteration % 10 == 0 and self.time % 60 < 5:
            await self.fortify_proxy()
            await self.fortify_expansions()
        await self.chronoboost()
        await self.build_workers()
        await self.build_pylons()
        await self.build_gas()
        await self.improve_military_tech()
        if not self.booming:
            await self.build_standing_military()
        await self.build_expansion()
        if self.attacking and iteration % 2 == 0:
            if len(self.get_combat_forces()) < 5:
                self.attacking = False
            await micro_army(self)
        else:
            await self.attack_when_ready()
        if self.units(CYBERNETICSCORE).ready.amount >= 1 and not self.proxy_built and self.can_afford(PYLON):
            for x in range(20, 40, 10):
                bot_logger.log_action(self, 'building proxy pylon')
                await build_proxy(self, distance_towards_location=x)
            self.proxy_built = True

    def get_workers_per_nexus(self):
        nexus_amount = self.units(NEXUS).amount
        return self.workers.amount / nexus_amount if nexus_amount > 0 else 0

    async def scout_enemy(self):
        scout = self.workers.random
        action_list = []
        for _ in range(100):
            position = self.enemy_start_locations[0].towards_with_random_angle(
                self.game_info.map_center, random.randrange(1, 5))
            action_list.append(scout.move(position))
        await self.do_actions(action_list)

    async def chronoboost(self):
        for nexus in self.units(NEXUS):
            available_nexus_abilities = await self.get_available_abilities(nexus)
            chronoboost = AbilityId.EFFECT_CHRONOBOOSTENERGYCOST
            if chronoboost in available_nexus_abilities:
                if self.is_researching_warpgate:
                    await chronoboost_building(self, nexus, self.units(CYBERNETICSCORE).ready.first)
                elif self.booming:
                    await chronoboost_building(self, nexus, self.townhalls.random)
                else:
                    await chronoboost_building(self, nexus)

    async def build_workers(self):
        worker_count = self.workers.amount
        nexus_count = self.units(NEXUS).amount
        workers_per_nexus = worker_count / nexus_count if nexus_count > 0 else worker_count
        if (workers_per_nexus >= 24 and not self.minerals > 800) or worker_count >= 70:
            return
        for nexus in self.units(NEXUS).ready.noqueue:
            if self.can_afford(PROBE):
                bot_logger.log_action(self, 'training probe')
                await self.do(nexus.train(PROBE))

    async def build_in_main(self, building, min_distance=8, max_distance=20):
        return await self.build(building, near=self.start_location.towards_with_random_angle(self.game_info.map_center, random.randrange(min_distance, max_distance)))

    async def build_pylons(self):
        if self.supply_left < 6 and self.supply_used < 195 and (not self.already_pending(PYLON) or self.minerals > 600) and self.can_afford(PYLON):
            bot_logger.log_action(self, 'building pylon')
            if self.units(PYLON).amount < 1:
                await self.build(PYLON, near=self.main_base_ramp.top_center)
            else:
                await self.build_in_main(PYLON, 5, 40)

    async def build_gas(self):
        for nexus in self.units(NEXUS).ready:
            if self.supply_used < 22:
                break
            if self.already_pending(ASSIMILATOR):
                break

            vespene_geysers = self.state.vespene_geyser.closer_than(
                10.0, nexus)
            for vespene_geyser in vespene_geysers:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vespene_geyser.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, vespene_geyser).exists:
                    bot_logger.log_action(self, 'building assimilator')
                    await self.do(worker.build(ASSIMILATOR, vespene_geyser))

    async def build_expansion(self):
        if not await self.get_next_expansion() or self.already_pending(NEXUS):
            return
        nexus_count = self.units(NEXUS).amount
        should_early_expand = nexus_count < 2 and self.time > 400
        if should_early_expand and self.can_afford(NEXUS):
            bot_logger.log_action(self, 'building expansion')
            await self.expand_now()
        elif self.minerals > max(nexus_count, 1) * 400:
            bot_logger.log_action(self, 'building expansion')
            try:
                r = await self.expand_now()
            except Exception as e:
                print(e)

    async def fortify_expansions(self):
        for expansion in self.owned_expansions:
            if self.units(PHOTONCANNON).closer_than(10, expansion).amount > 1:
                continue
            if self.can_afford(PYLON):
                await self.build(PYLON, near=expansion)
            for pylon in self.units(PYLON).closer_than(10, expansion):
                if self.can_afford(PHOTONCANNON):
                    await self.build(PHOTONCANNON, near=pylon)

    async def fortify_proxy(self):
        if self.proxy_built:
            proxy_pylon = get_closest_pylon_to_enemy_base(self)
            if self.can_afford(PYLON) and self.units(PYLON).closer_than(20, proxy_pylon).amount < 3:
                await self.build(PYLON, near=proxy_pylon.position.towards_with_random_angle(self.enemy_start_locations[0], 10))
            if self.units(FORGE).ready.exists and self.can_afford(PHOTONCANNON) and self.units(PHOTONCANNON).closer_than(10, proxy_pylon).amount < 3:
                await self.build(PHOTONCANNON, near=proxy_pylon.position.towards_with_random_angle(self.enemy_start_locations[0], 3))

    async def improve_military_tech(self):
        if self.units(PYLON).ready.exists:
            pylon = self.units(PYLON).ready.closer_than(
                50, self.start_location).first

            if self.units(GATEWAY).ready.exists:
                # build a cybernetics core
                if not self.units(CYBERNETICSCORE):
                    if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                        bot_logger.log_action(
                            self, 'buildilng cybernetics core')
                        await self.build(CYBERNETICSCORE, near=pylon)
                # builds robotics facilities
                elif not self.already_pending(ROBOTICSFACILITY) and self.can_afford(ROBOTICSFACILITY):
                    if not self.units(ROBOTICSFACILITY) and self.time > 250:
                        await self.build(ROBOTICSFACILITY, near=pylon)
                    if self.time > 400 and self.units(ROBOTICSFACILITY).amount < 2:
                        await self.build(ROBOTICSFACILITY, near=pylon)
                # research warpgate
                elif self.units(CYBERNETICSCORE).ready.exists and self.can_afford(AbilityId.RESEARCH_WARPGATE) and not self.warpgate_started:
                    cybercore = self.units(CYBERNETICSCORE).ready.first
                    await self.do(cybercore(AbilityId.RESEARCH_WARPGATE))
                    self.warpgate_started = True
                    self.warpgate_start_time = self.time

                # manage warpgate_finished
                if not self.warpgate_finished and self.is_researching_warpgate and not self.time - \
                        self.warpgate_start_time > 120:
                    self.warpgate_finished = True

            gateway_warpgate_count = self.units(
                GATEWAY).amount + self.units(WARPGATE).amount
            # build first gateway
            if gateway_warpgate_count < 1:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    bot_logger.log_action(self, 'building first gateway')
                    await self.build(GATEWAY, near=pylon)
            # build second gateway
            if gateway_warpgate_count < 2 and self.time > 200 and not self.already_pending(GATEWAY):
                if self.can_afford(GATEWAY):
                    bot_logger.log_action(self, 'building second gateway')
                    await self.build(GATEWAY, near=pylon)
            # build third gatway
            if gateway_warpgate_count < 3 and self.time > 300 and not self.already_pending(GATEWAY):
                if self.can_afford(GATEWAY):
                    bot_logger.log_action(self, 'building third gateway')
                    await self.build(GATEWAY, near=pylon)
            # build 4-20 gateways
            if gateway_warpgate_count >= 3 and gateway_warpgate_count < 20 and self.minerals > 900 and self.time > 300 and not self.already_pending(GATEWAY):
                if self.can_afford(GATEWAY):
                    bot_logger.log_action(self,
                                          'building gateway #{}'.format(gateway_warpgate_count))
                    await self.build(GATEWAY, near=pylon)

            if self.time > 300:
                # build forge
                if not self.units(FORGE).ready.amount > 1 and not self.already_pending(FORGE) and self.can_afford(FORGE):
                    bot_logger.log_action(self, 'building forge')
                    await self.build(FORGE, near=pylon)
                # manage forge upgrades
                else:
                    for forge in self.units(FORGE).ready.noqueue:
                        if forge:
                            forge_abilities = await self.get_available_abilities(forge)
                            for upgrade in self.all_upgrades:
                                if upgrade in forge_abilities and self.minerals > 400 and self.vespene > 400:
                                    bot_logger.log_action(self,
                                                          'buying upgrade {}'.format(upgrade))
                                    return await self.do(forge(upgrade))

            if self.time > 550:
                # build twlighlight council
                has_twilight = self.units(TWILIGHTCOUNCIL).ready.exists
                if not has_twilight and not self.already_pending(TWILIGHTCOUNCIL) and self.can_afford(TWILIGHTCOUNCIL):
                    await self.build(TWILIGHTCOUNCIL, near=pylon)
                elif has_twilight:
                    twilight_council = self.units(TWILIGHTCOUNCIL).ready.first
                    twilight_abilities = await self.get_available_abilities(twilight_council)
                    twilight_upgrades = [
                        AbilityId.RESEARCH_CHARGE
                    ]
                    for upgrade in twilight_upgrades:
                        if upgrade in twilight_abilities and self.minerals > 400 and self.vespene > 400:
                            bot_logger.log_action(self,
                                                  'buying upgrade {}'.format(upgrade))
                            return await self.do(twilight_council(upgrade))
                            self.zealot_charge_started = True

    async def build_standing_military(self):
        has_cybercore = self.units(CYBERNETICSCORE).ready.exists
        for robo in self.units(ROBOTICSFACILITY).ready.noqueue:
            if self.can_afford(IMMORTAL):
                bot_logger.log_action(self, 'training immortal')
                await self.do(robo.train(IMMORTAL))
        if not self.warpgate_finished:
            for gateway in self.units(GATEWAY).ready.noqueue:
                if has_cybercore and self.vespene > 0 and self.minerals / self.vespene < .3 and self.can_afford(SENTRY):
                    bot_logger.log_action(self, 'training sentry')
                    await self.do(gateway.train(SENTRY))
                elif has_cybercore and self.can_afford(STALKER):
                    bot_logger.log_action(self, 'training stalker')
                    await self.do(gateway.train(STALKER))
                elif self.can_afford(ZEALOT):
                    bot_logger.log_action(self, 'training zealot')
                    await self.do(gateway.train(ZEALOT))
        if self.units(PYLON).exists:
            proxy_pylon = get_closest_pylon_to_enemy_base(self)
            await self.warp_new_units(proxy_pylon)

    def get_military_buildings(self):
        gateways = self.units(GATEWAY).ready
        robos = self.units(ROBOTICSFACILITY).ready
        return gateways + robos

    def get_rally_point(self):
        if self.proxy_built:
            proxy_pylon = get_closest_pylon_to_enemy_base(self)
            if proxy_pylon:
                return proxy_pylon.position.towards(self.enemy_start_locations[0], 3)
        return self.game_info.map_center if self.attacking else self.main_base_ramp.top_center

    def rally_building(self, building, rally_point=None):
        return self.do(building(AbilityId.RALLY_BUILDING, rally_point if rally_point else self.get_rally_point()))

    async def position_army(self):
        actions = []
        if self.proxy_built:
            for unit in self.get_idle_combat_forces():
                actions.append(
                    unit.move(get_closest_pylon_to_enemy_base(self)))
        await self.do_actions(actions)

    async def set_rally_points(self):
        print('setting rally points')
        for military_building in self.get_military_buildings():
            available_military_building_abilities = await self.get_available_abilities(military_building)
            if AbilityId.RALLY_BUILDING in available_military_building_abilities:
                await self.rally_building(military_building)
        for nexus in self.units(NEXUS).ready:
            closest_minerals = self.state.mineral_field.closest_to(nexus)
            await self.rally_building(nexus, rally_point=closest_minerals)

    def get_combat_forces(self):
        zealots = self.units(ZEALOT)
        stalkers = self.units(STALKER)
        sentries = self.units(SENTRY)
        immortals = self.units(IMMORTAL)
        return zealots + stalkers + sentries + immortals

    def get_idle_combat_forces(self):
        zealots = self.units(ZEALOT).idle
        stalkers = self.units(STALKER).idle
        sentries = self.units(SENTRY).idle
        immortals = self.units(IMMORTAL).idle
        return zealots + stalkers + sentries + immortals

    async def attack_when_ready(self):
        all_combat_units = self.get_combat_forces()
        total_combat_unit_count = len(all_combat_units)
        actions = []
        if total_combat_unit_count > max(self.attack_count, 1) * 20 or self.supply_used > 180:
            for unit in self.get_idle_combat_forces():
                self.attacking = True
                self.attack_count += 1
                actions.append(unit.attack(self.enemy_start_locations[0]))
        elif total_combat_unit_count > 2:
            for expansion in self.owned_expansions:
                if self.known_enemy_units.closer_than(5, expansion).amount > 0:
                    for unit in all_combat_units:
                        actions.append(unit.attack(
                            self.known_enemy_units.closest_to(unit.position)))
            if self.proxy_built:
                proxy_pylon = get_closest_pylon_to_enemy_base(self)
                if proxy_pylon and self.known_enemy_units.closer_than(10, proxy_pylon).amount > 0:
                    for unit in all_combat_units:
                        actions.append(unit.attack(
                            self.known_enemy_units.closest_to(unit.position)
                        ))
            await self.do_actions(actions)

    async def warp_new_units(self, proxy: Unit):
        for warpgate in self.units(WARPGATE).ready:
            abilities = await self.get_available_abilities(warpgate)
            # all the units have the same cooldown anyway so let's just look at ZEALOT
            if AbilityId.WARPGATETRAIN_ZEALOT in abilities:
                pos = proxy.position.to2.random_on_distance(4)
                placement = await self.find_placement(AbilityId.WARPGATETRAIN_STALKER, pos, placement_step=1)
                if placement is None:
                    # return ActionResult.CantFindPlacementLocation
                    print("can't place")
                    return
                # make stalkers when possible. 70% chance after zealot charge
                if (not self.zealot_charge_started or random.randrange(100) < 40) and self.can_afford(STALKER):
                    bot_logger.log_action(
                        self, 'warping in stalker {}'.format(placement))
                    await self.do(warpgate.warp_in(STALKER, placement))
                elif self.can_afford(SENTRY) and self.minerals / self.vespene < .3:
                    bot_logger.log_action(
                        self, 'warping in sentry {}'.format(placement))
                    await self.do(warpgate.warp_in(SENTRY, placement))
                elif self.can_afford(ZEALOT):
                    bot_logger.log_action(
                        self, 'warping in zealot {}'.format(placement))
                    await self.do(warpgate.warp_in(ZEALOT, placement))
                else:
                    return
