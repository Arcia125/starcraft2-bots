import random
import sc2
import logging
from sc2.unit import Unit
from sc2.units import Units
from sc2.constants import AbilityId, BuffId, UnitTypeId
from sc2.unit_command import UnitCommand
from typing import List

import src.bot_logger as bot_logger
from src.helpers import roundrobin, between
from src.bot_actions import build_building_once, get_workers_per_townhall, has_enemies_nearby
from src.zerg_actions import get_random_larva, build_drone, build_zergling, build_overlord, upgrade_zergling_speed, get_forces, geyser_has_extractor


class ZerglingMutaBot(sc2.BotAI):
    @property
    def is_booming_time(self):
        now = self.time
        return any(between(now, minimum, maximum) for minimum, maximum in self.boom_timings)

    @property
    def is_booming(self):
        return self.is_booming_time

    @property
    def is_rushing_time(self):
        now = self.time
        return any(between(now, minimum, maximum) for minimum, maximum in self.rush_timings)

    @property
    def is_rushing(self):
        return self.is_rushing_time or self.units(UnitTypeId.MUTALISK).ready.amount > 10

    def get_has_been_under_attack_recently(self, is_under_attack=False) -> bool:
        recent_combat = self.time - \
            self.last_defensive_situation_time < 20 if self.last_defensive_situation_time else False
        return is_under_attack or recent_combat

    async def on_unit_created(self, unit: Unit):
        """automatically called by base class"""
        if unit.type_id is UnitTypeId.DRONE:
            await self.distribute_workers()

    async def on_building_construction_complete(self, unit: Unit):
        if unit.type_id is UnitTypeId.EXTRACTOR:
            await self.distribute_workers()

    def get_townhalls_under_attack(self) -> Units:
        return self.townhalls.filter(lambda townhall: has_enemies_nearby(bot=self, position=townhall, distance=20))

    def manage_booming(self):
        if self.is_booming:
            if not self.booming:
                bot_logger.log_action(
                    self, '-- starting boom period {} --'.format(self.time))
                self.booming = True
        else:
            if self.booming:
                bot_logger.log_action(
                    self, '-- ending boom period {} --'.format(self.time))
                self.booming = False

    def manage_rushing(self):
        if self.is_rushing:
            if not self.rushing:
                bot_logger.log_action(
                    self, '** starting rush period {} **'.format(self.time))
                self.rushing = True
        else:
            if self.rushing:
                bot_logger.log_action(
                    self, '** ending rush period {} **'.format(self.time))
                self.rushing = False

    def on_start(self):
        self.max_worker_count = 100
        self.ideal_workers_per_hatch = 24
        self.metabolic_boost_started = False
        self.adrenal_glands_started = False
        self.use_mutalisk_strategy = True
        # ? how / when should this be enabled
        self.use_ultralisk_strategy = False
        self.booming = True
        self.boom_timings = [
            (0, 420),
            (475, 775),
            (800, 1000),
            (1500, 1900)
        ]
        self.rushing = False
        self.rush_timings = [
            (430, 475),
            (800, 850),
            (950, 1000),
            (1200, 1300),
            (1900, 2500)
        ]
        self.has_been_attacked = False
        self.last_defensive_situation_time = None
        self.expansion_count = 0
        self.last_expansion_time = 0
        self.evolution_chamber_melee_attack_upgrades = [
            AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL1,
            AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL2,
            AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL3
        ]
        self.evolution_chamber_armor_upgrades = [
            AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL1,
            AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL1,
            AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL2
        ]
        self.evolution_chamber_upgrades = roundrobin(
            self.evolution_chamber_melee_attack_upgrades, self.evolution_chamber_armor_upgrades)
        self.spire_attack_upgrades = [
            AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL1,
            AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL2,
            AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL3
        ]
        self.spire_defense_upgrades = [
            AbilityId.RESEARCH_ZERGFLYERARMORLEVEL1,
            AbilityId.RESEARCH_ZERGFLYERARMORLEVEL2,
            AbilityId.RESEARCH_ZERGFLYERARMORLEVEL3
        ]
        self.spire_upgrades = roundrobin(
            self.spire_attack_upgrades, self.spire_defense_upgrades)

    async def should_build_lair(self):
        return self.can_afford(UnitTypeId.LAIR) and await self.can_cast(self.townhalls.first, AbilityId.UPGRADETOLAIR_LAIR)

    def should_build_hive(self):
        return self.units(UnitTypeId.INFESTATIONPIT).ready.exists and not self.units(
            UnitTypeId.HIVE).ready.exists and not self.already_pending(UnitTypeId.HIVE) and self.can_afford(UnitTypeId.HIVE)

    def should_build_spire(self):
        return self.use_mutalisk_strategy and not self.units(
            UnitTypeId.SPIRE).ready.exists and not self.already_pending(UnitTypeId.SPIRE)

    async def on_step(self, iteration):
        townhalls_under_attack = self.get_townhalls_under_attack()
        is_under_attack = townhalls_under_attack.amount > 0
        if iteration == 0:
            await self.first_iteration()
        if iteration % 8 == 0:
            self.manage_booming()
            self.manage_rushing()
            if is_under_attack:
                self.last_defensive_situation_time = self.time
                # pull drones from hatcheries that are under attack
                actions = []
                for townhall in townhalls_under_attack:
                    drones = self.units(
                        UnitTypeId.DRONE).closer_than(20, townhall)
                    if drones.exists:
                        for drone in drones:
                            actions.append(drone.move(self.start_location))
                await self.do_actions(actions)

        has_been_under_attack_recently = self.get_has_been_under_attack_recently(
            is_under_attack=is_under_attack)
        if iteration % 50:
            # build queens
            for townhall in self.townhalls.ready.noqueue:
                if self.units(UnitTypeId.QUEEN).ready.closer_than(5, townhall).amount < 1:
                    if self.can_afford(UnitTypeId.QUEEN) and self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and not self.already_pending(UnitTypeId.QUEEN):
                        await self.do(townhall.train(UnitTypeId.QUEEN))

        # we're losing, go for broke.
        if not self.townhalls.exists:
            target = self.select_target()
            if iteration % 50 == 0:
                actions = []
                for unit in self.workers | self.units(UnitTypeId.QUEEN) | get_forces(self):
                    actions.append(unit.attack(target))
                await self.do_actions(actions)
            return

        if iteration % 150 == 0:
            await self.distribute_workers()
            await self.set_rally_points()

        await self.improve_military_tech()

        if not has_been_under_attack_recently and self.should_build_gas():
            await self.build_gas()

        if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and iteration % 50 == 0:
            if not self.units(UnitTypeId.LAIR).ready.exists and self.townhalls.first:
                if await self.should_build_lair():
                    if not self.already_pending(UnitTypeId.LAIR) > 0 and not self.units(UnitTypeId.LAIR).exists:
                        bot_logger.log_action(self, "building lair")
                        await self.do(self.townhalls.ready.first.build(UnitTypeId.LAIR))
            elif self.should_build_spire():
                bot_logger.log_action(self, "building spire")
                await self.build(UnitTypeId.SPIRE, near=self.start_location)

            if self.should_build_hive():
                lair = self.units(UnitTypeId.LAIR).ready.noqueue.exists and self.units(UnitTypeId.LAIR).ready.noqueue.closest_to(
                    self.start_location)
                if lair and not self.already_pending(UnitTypeId.HIVE):
                    await self.do(lair.build(UnitTypeId.HIVE))

        if not (is_under_attack or has_been_under_attack_recently) and self.should_build_drones():
            await self.build_drones()
        await self.build_units(is_under_attack=is_under_attack)

        for queen in self.units(UnitTypeId.QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.do(queen(AbilityId.EFFECT_INJECTLARVA, self.townhalls.closest_to(queen)))
        townhall_count = self.townhalls.ready.amount
        if townhall_count < 3 or self.time > 500 and not has_been_under_attack_recently and get_workers_per_townhall(self) > 14:
            if (not self.already_pending(UnitTypeId.HATCHERY) or (self.booming and self.time > 500)) and await self.get_next_expansion() and self.can_afford(UnitTypeId.HATCHERY) and (get_forces(self).ready.amount > 10 or self.expansion_count < 1) and self.time - self.last_expansion_time > 10:
                self.expansion_count += 1
                self.last_expansion_time = self.time
                bot_logger.log_action(
                    self, "taking expansion #{} at time: {} with {} workers per hatchery".format(self.expansion_count, self.time, get_workers_per_townhall(self)))
                await self.expand_now(max_distance=5)

        await self.micro_army(iteration=iteration, is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)

    def get_rally_point(self):
        return self.game_info.map_center if self.rushing else self.townhalls.center

    def rally_building(self, building, rally_point=None):
        return self.do(building(AbilityId.RALLY_BUILDING, rally_point if rally_point else self.get_rally_point()))

    async def set_rally_points(self):
        bot_logger.log_action(self, 'setting rally points')
        for townhall in self.townhalls.ready:
            available_townhall_abilities = await self.get_available_abilities(townhall)
            if AbilityId.RALLY_BUILDING in available_townhall_abilities:
                await self.rally_building(townhall)
                closest_minerals = self.state.mineral_field.closest_to(
                    townhall)
                await self.do(townhall(AbilityId.RALLY_WORKERS, closest_minerals))

    async def micro_army(self, iteration=None, is_under_attack=False, townhalls_under_attack=[]):
        actions = []
        actions = actions + \
            self.micro_idle(is_under_attack=is_under_attack)
        actions = actions + \
            self.micro_zerglings(
                is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)
        actions = actions + \
            self.micro_mutalisks(
                is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)
        actions = actions + \
            self.micro_ultralisks(is_under_attack=is_under_attack)
        actions = actions + \
            self.micro_overlords(iteration)
        await self.do_actions(actions)

    def micro_idle(self, is_under_attack=False) -> List[UnitCommand]:
        actions = []
        target = self.get_rally_point()
        for unit in get_forces(self).idle.further_than(10, target):
            actions.append(unit.move(target))
        return actions

    def micro_zerglings(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        unit_id = UnitTypeId.ZERGLING
        zerglings = self.units(unit_id).ready
        actions = []
        for zergling in zerglings:
            enemy_threats = self.known_enemy_units.filter(
                lambda x: x.can_attack_ground and not x.is_flying).closer_than(10, zergling)
            if townhalls_under_attack:
                actions.append(zergling.attack(self.known_enemy_units.closest_to(
                    Units(townhalls_under_attack, self._game_data).closest_to(zergling))))
                continue
            if enemy_threats.exists:
                closest_enemy = enemy_threats.sorted_by_distance_to(
                    zergling).first
                actions.append(zergling.attack(closest_enemy))
            elif is_under_attack:
                target = self.known_enemy_units.closest_to(zergling)
                actions.append(zergling.attack(target))
            elif self.rushing or self.supply_used > 190:
                target = self.select_target()
                actions.append(zergling.attack(target))
        return actions

    def micro_mutalisks(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        unit_id = UnitTypeId.MUTALISK
        mutalisks = self.units(unit_id).ready
        actions = []
        for mutalisk in mutalisks:
            if mutalisk.health_percentage < .33:
                actions.append(mutalisk.move(self.start_location))
                continue
            flying_threats = self.known_enemy_units.filter(
                lambda x: x.can_attack_air).closer_than(15, mutalisk)
            if townhalls_under_attack:
                actions.append(mutalisk.attack(self.known_enemy_units.closest_to(
                    Units(townhalls_under_attack, self._game_data).closest_to(mutalisk))))
                continue
            if flying_threats.exists:
                actions.append(mutalisk.attack(
                    flying_threats.closest_to(mutalisk)))
                continue
            enemy_threats = self.known_enemy_units.exclude_type(UnitTypeId.LARVA).filter(
                lambda x: x.health <= 50 or x.is_attacking).closer_than(10, mutalisk)
            if enemy_threats.exists:
                closest_enemy = enemy_threats.sorted_by_distance_to(
                    mutalisk).first
                if mutalisk.weapon_cooldown == 0:
                    actions.append(mutalisk.attack(closest_enemy))
                elif closest_enemy.distance_to(mutalisk) < mutalisk.ground_range - 2:
                    actions.append(mutalisk.move(
                        closest_enemy.position.towards(mutalisk, mutalisk.ground_range)))
            elif is_under_attack:
                target = self.known_enemy_units.random_or(
                    self.known_enemy_structures.random_or(self.enemy_start_locations[0]))
                actions.append(mutalisk.attack(target))
            elif self.rushing or self.supply_used > 190:
                target = self.select_target()
                actions.append(mutalisk.attack(target))
        return actions

    def micro_ultralisks(self, is_under_attack=False) -> List[UnitCommand]:
        unit_id = UnitTypeId.ULTRALISK
        ultralisks = self.units(unit_id).ready
        actions = []
        for ultralisk in ultralisks:
            enemy_threats = self.known_enemy_units.filter(
                lambda x: x.can_attack_ground).closer_than(10, ultralisk)
            if enemy_threats.exists:
                closest_enemy = enemy_threats.closest_to(ultralisk)
                actions.append(ultralisk.attack(closest_enemy))
            elif is_under_attack:
                target = self.known_enemy_units.random_or(
                    self.known_enemy_structures.random_or(self.enemy_start_locations[0]))
                actions.append(ultralisk.attack(target))
            elif self.rushing or self.supply_used > 190:
                target = self.select_target()
                actions.append(ultralisk.attack(target))
        return actions

    def micro_overlords(self, iteration) -> List[UnitCommand]:
        unit_id = UnitTypeId.OVERLORD
        overlords = self.units(unit_id).ready
        actions = []
        if iteration % 50 == 0 and self.units(UnitTypeId.LAIR).ready.exists or self.units(UnitTypeId.HIVE).ready.exists:
            for overlord in overlords:
                actions.append(overlord(AbilityId.BEHAVIOR_GENERATECREEPON))
        if iteration % 10 == 0 and self.time % 60 < 1 and self.time > 300:
            for townhall in self.townhalls.ready:
                for overlord in self.units(unit_id).ready.idle.closer_than(10, townhall):
                    actions.append(overlord.move(
                        self.state.mineral_field.further_than(40, self.enemy_start_locations[0]).random))
        return actions

    async def first_iteration(self):
        await self.distribute_workers()
        await self.scout_enemy()

    def select_target(self):

        if self.known_enemy_structures.exists:
            return random.choice(self.known_enemy_structures).position

        if self.time < 400:
            return self.enemy_start_locations[0].closest(self.expansion_locations)

        return self.enemy_start_locations[0]

    async def scout_enemy(self):
        scout = self.workers.random if self.time < 200 else self.units(
            UnitTypeId.ZERGLING).idle.random
        action_list = []
        start_location = random.choice(self.enemy_start_locations)
        for _ in range(100):
            position = start_location.towards_with_random_angle(
                self.game_info.map_center, random.randrange(1, 5))
            action_list.append(scout.move(position, queue=True))
        await self.do_actions(action_list)

    def should_build_drones(self):
        worker_count = self.workers.amount
        townhalls_with_mineral_fields = 0
        for location, _ in self.owned_expansions.items():
            if self.state.mineral_field.closer_than(10, location).exists:
                townhalls_with_mineral_fields += 1
        workers_per_hatch = worker_count / \
            townhalls_with_mineral_fields if townhalls_with_mineral_fields else worker_count
        ideal_workers_per_hatch_met = workers_per_hatch >= self.ideal_workers_per_hatch
        is_worker_count_under_maximum = worker_count < self.max_worker_count
        has_available_larva = self.units(UnitTypeId.LARVA).ready.amount > 0
        result = has_available_larva and is_worker_count_under_maximum and self.booming and not ideal_workers_per_hatch_met
        return result

    def can_build_drone(self):
        return self.supply_left > 1 and self.can_afford(UnitTypeId.DRONE)

    async def build_drones(self):
        if self.can_build_drone():
            return await build_drone(self)

    async def handle_evo_chamber_upgrades(self):
        for evo_chamber in self.units(UnitTypeId.EVOLUTIONCHAMBER).ready.noqueue:
            evo_chamber_abilities = await self.get_available_abilities(evo_chamber)
            for upgrade in self.evolution_chamber_upgrades:
                if upgrade in evo_chamber_abilities and self.minerals > 300 and self.vespene > 300:
                    bot_logger.log_action(
                        self, 'buying upgrade {}'.format(upgrade))
                    await self.do(evo_chamber(upgrade))
                    return

    async def handle_spire_upgrades(self):
        for spire in self.units(UnitTypeId.SPIRE).ready.noqueue:
            spire_abilities = await self.get_available_abilities(spire)
            for upgrade in self.spire_upgrades:
                if upgrade in spire_abilities and self.minerals > 400 and self.vespene > 400:
                    bot_logger.log_action(
                        self, 'buying upgrade {}'.format(upgrade))
                    await self.do(spire(upgrade))
                    return

    async def upgrade_military(self):
        await self.handle_evo_chamber_upgrades()
        if self.use_mutalisk_strategy:
            await self.handle_spire_upgrades()

    def should_build_infestation_pit(self) -> bool:
        return self.supply_used > 100 and not self.units(UnitTypeId.INFESTATIONPIT).ready.exists and self.can_afford(UnitTypeId.INFESTATIONPIT) and not self.already_pending(UnitTypeId.INFESTATIONPIT) and self.units(UnitTypeId.SPIRE).ready.exists

    def should_build_ultralisk_den(self) -> bool:
        return self.use_ultralisk_strategy and not self.units(UnitTypeId.ULTRALISKCAVERN) and not self.already_pending(UnitTypeId.ULTRALISKCAVERN) and self.can_afford(UnitTypeId.ULTRALISKCAVERN)

    def should_check_if_should_research_adrenal_glands(self) -> bool:
        return self.units(UnitTypeId.SPAWNINGPOOL).ready.noqueue.exists and self.can_afford(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS)

    def should_build_evolution_chamber(self) -> bool:
        return self.expansion_count > 1 and not self.units(UnitTypeId.EVOLUTIONCHAMBER).amount >= 2 and self.can_afford(UnitTypeId.EVOLUTIONCHAMBER) and not self.already_pending(UnitTypeId.EVOLUTIONCHAMBER)

    async def improve_military_tech(self):
        if self.expansion_count > 0:
            await build_building_once(self, UnitTypeId.SPAWNINGPOOL, self.start_location.towards_with_random_angle(self.game_info.map_center, random.randrange(5, 12)))
        if not self.metabolic_boost_started:
            started_upgrade = await upgrade_zergling_speed(self)
            if started_upgrade:
                self.metabolic_boost_started = True
        if self.should_build_infestation_pit():
            bot_logger.log_action(self, 'building infestation pit')
            await self.build(UnitTypeId.INFESTATIONPIT, near=self.townhalls.closest_to(self.start_location))
        if self.units(UnitTypeId.HIVE).ready.exists:
            if self.should_build_ultralisk_den():
                bot_logger.log_action(self, 'building ultralisk cavern')
                await self.build(UnitTypeId.ULTRALISKCAVERN, near=self.townhalls.closest_to(self.start_location))
            if self.should_check_if_should_research_adrenal_glands():
                spawning_pool = self.units(
                    UnitTypeId.SPAWNINGPOOL).ready.noqueue
                if not spawning_pool.exists:
                    return
                spawning_pool = spawning_pool.first
                spawning_pool_abilities = await self.get_available_abilities(spawning_pool)
                if AbilityId.RESEARCH_ZERGLINGADRENALGLANDS in spawning_pool_abilities and not self.adrenal_glands_started:
                    bot_logger.log_action(self, 'upgrading adrenal glands')
                    self.adrenal_glands_started = True
                    await self.do(spawning_pool(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS))

        if self.should_build_evolution_chamber():
            await self.build(UnitTypeId.EVOLUTIONCHAMBER, near=self.townhalls.closest_to(self.start_location))
        await self.upgrade_military()

    async def build_units(self, is_under_attack=False):
        if self.units(UnitTypeId.LARVA).amount <= 0:
            return

        if (self.supply_left < 4 or self.minerals > 1500) and not self.already_pending(UnitTypeId.OVERLORD) and not self.supply_cap == 200:
            await build_overlord(self, None)
            if self.time > 200:
                await build_overlord(self, None)
            if self.time > 400:
                await build_overlord(self, None)
        for larva in self.units(UnitTypeId.LARVA).ready:
            if self.supply_left < 0:
                return
            if self.use_ultralisk_strategy and self.can_afford(UnitTypeId.ULTRALISK) and self.units(UnitTypeId.ULTRALISKCAVERN).ready.exists:
                bot_logger.log_action(self, "building ultralisk")
                await self.do(larva.train(
                    UnitTypeId.ULTRALISK
                ))
            elif self.use_mutalisk_strategy and self.can_afford(UnitTypeId.MUTALISK) and self.units(UnitTypeId.SPIRE).ready.exists and self.supply_left > 2:
                bot_logger.log_action(self, "building mutalisk")
                await self.do(larva.train(
                    UnitTypeId.MUTALISK))
            elif self.vespene < 100 or self.minerals / self.vespene > .3:
                await build_zergling(self, larva)

    def should_build_gas(self) -> bool:
        extractors = self.units(UnitTypeId.EXTRACTOR)
        extractor_count = extractors.amount
        if extractor_count < 1 and self.expansion_count < 1 and self.time > 60:
            return True
        elif extractor_count < 2 and self.time > 120:
            return True
        elif extractor_count < 3 and self.time > 300:
            return True
        elif extractor_count < 4 and self.time > 500:
            return True
        elif extractor_count >= 4:
            return True
        else:
            return False

    def can_build_gas(self) -> bool:
        return self.can_afford(UnitTypeId.EXTRACTOR)

    async def build_gas(self):
        for hatch in self.townhalls.ready:
            if self.supply_used < 16:
                break
            if self.already_pending(UnitTypeId.EXTRACTOR):
                break

            vespene_geysers = self.state.vespene_geyser.closer_than(
                10.0, hatch)
            for vespene_geyser in vespene_geysers:
                if not self.can_build_gas():
                    break
                worker = self.select_build_worker(vespene_geyser.position)
                if worker is None:
                    break
                if not geyser_has_extractor(self, vespene_geyser):
                    bot_logger.log_action(self, 'building extractor')
                    await self.do(worker.build(UnitTypeId.EXTRACTOR, vespene_geyser))
