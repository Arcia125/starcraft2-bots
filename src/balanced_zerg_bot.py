import random
import sc2
import math
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.constants import AbilityId, BuffId, UnitTypeId, UpgradeId
from sc2.unit_command import UnitCommand
from typing import List, Callable

import src.bot_logger as bot_logger
from src.helpers import roundrobin, between, value_between_any, property_cache_forever
from src.bot_actions import build_building_once, get_workers_per_townhall, get_enemies_near_position, find_potential_enemy_expansions, get_is_targettable_callable, get_is_threat_callable
from src.zerg_actions import get_random_larva, build_drone, build_zergling, build_overlord, \
    upgrade_zergling_speed, get_forces, geyser_has_extractor, already_researching_lair, \
    already_researching_hive, ZERG_MELEE_WEAPON_UPGRADES, ZERG_RANGED_WEAPON_UPGRADES, \
    ZERG_GROUND_ARMOR_UPGRADES, ZERG_FLYING_WEAPON_UPGRADES, ZERG_FLYING_ARMOR_UPGRADES, \
    ULTRALISK_DEN_ABILITIES, ROACHWARREN_ABILITIES
from src.zerg_bot_base import ZergBotBase


class BalancedZergBot(ZergBotBase):
    def __init__(self,
        # TODO make class wrapper for timings
        boom_timings=[
            (-1, 420),
            (475, 775),
            (800, 1000),
            (1500, 1900),
            (2000, math.inf)
        ],
        rush_timings=[
            (430, 475),
            (800, 850),
            (950, 1000),
            (1250, 1300),
            (1450, 1500),
            (1650, 1700),
            (1850, 1900),
            (2050, 2100),
            (2250, 2300),
            (2600, math.inf)
        ],
        mutalisk_timings=[
            (-1, 700),
            (900, math.inf)
        ],
        ultralisk_timings=[
            (400, math.inf)
        ],
        roach_timings=[
            (400, 600),
            (1000, math.inf)
        ],
        hydralisk_timings=[
            (450, math.inf)
        ]
    ):
        super().__init__()
        self.boom_timings = boom_timings
        self.rush_timings = rush_timings
        self.mutalisk_timings = mutalisk_timings
        self.ultralisk_timings = ultralisk_timings
        self.roach_timings = roach_timings
        self.hydralisk_timings = hydralisk_timings

    @property
    def _is_booming_time(self):
        now = self.time
        return value_between_any(now, self.boom_timings)

    @property
    def _is_booming(self):
        return self._is_booming_time

    @property
    def _is_rushing_time(self):
        now = self.time
        return value_between_any(now, self.rush_timings)

    @property
    def _is_mutalisk_time(self):
        now = self.time
        return value_between_any(now, self.mutalisk_timings)

    @property
    def _is_ultralisk_time(self):
        now = self.time
        return value_between_any(now, self.ultralisk_timings)

    @property
    def _is_roach_time(self):
        now = self.time
        return value_between_any(now, self.roach_timings)

    @property
    def _is_hydralisk_time(self):
        now = self.time
        return value_between_any(now, self.hydralisk_timings)

    @property
    def _is_rushing(self):
        # TODO add conditions
        return self._is_rushing_time

    @property_cache_forever
    def potential_enemy_expansions(self) -> List[Point2]:
        return find_potential_enemy_expansions(self)

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
        return self.townhalls.filter(lambda townhall: get_enemies_near_position(bot=self, position=townhall, distance=20, unit_filter=lambda u: u.can_attack_ground and u.ground_dps > 5).exists)

    def manage_booming(self):
        if self._is_booming:
            if not self.booming:
                bot_logger.log_strategy_start(self, 'booming')
                self.booming = True
        else:
            if self.booming:
                bot_logger.log_strategy_end(self, 'booming')
                self.booming = False

    def manage_rushing(self):
        if self._is_rushing:
            if not self.rushing:
                bot_logger.log_strategy_start(self, 'rushing')
                self.rushing = True
        else:
            if self.rushing:
                bot_logger.log_strategy_end(self, 'rushing')
                self.rushing = False

    def manage_mutalisk_strategy(self):
        if self._is_mutalisk_time:
            if not self.use_mutalisk_strategy:
                bot_logger.log_strategy_start(self, 'mutalisk')
                self.use_mutalisk_strategy = True
        else:
            if self.use_mutalisk_strategy:
                bot_logger.log_strategy_end(self, 'mutalisk')
                self.use_mutalisk_strategy = False

    def manage_ultralisk_strategy(self):
        if self._is_ultralisk_time:
            if not self.use_ultralisk_strategy:
                bot_logger.log_strategy_start(self, 'ultralisk')
                self.use_ultralisk_strategy = True
        else:
            if self.use_ultralisk_strategy:
                bot_logger.log_strategy_end(self, 'ultralisk')
                self.use_ultralisk_strategy = False

    def manage_roach_strategy(self):
        if self._is_roach_time:
            if not self.use_roach_strategy:
                bot_logger.log_strategy_start(self, 'roach')
                self.use_roach_strategy = True
        else:
            if self.use_roach_strategy:
                bot_logger.log_strategy_end(self, 'roach')
                self.use_roach_strategy = False

    def manage_hydralisk_strategy(self):
        if self._is_hydralisk_time:
            if not self.use_hydralisk_strategy:
                bot_logger.log_strategy_start(self, 'hydralisk')
                self.use_hydralisk_strategy = True
        else:
            if self.use_hydralisk_strategy:
                bot_logger.log_strategy_end(self, 'hydralisk')
                self.use_hydralisk_strategy = False

    def manage_strategies(self):
        self.manage_booming()
        self.manage_rushing()
        self.manage_roach_strategy()
        self.manage_mutalisk_strategy()
        self.manage_ultralisk_strategy()

    def on_start(self):
        # settings
        self.max_worker_count = 100
        self.ideal_workers_per_hatch = 24

        # milestones
        self.metabolic_boost_started = False
        self.adrenal_glands_started = False
        self.burrow_started = False

        # event memories
        self.expansion_count = 0
        self.last_expansion_time = 0
        self.last_defensive_situation_time = None

        # strategy toggles (these are all managed, see the __init__ method for timings,
        # and the manage_strategies method for the heuristics that enable / disable these properties)
        self.use_mutalisk_strategy = False
        self.use_ultralisk_strategy = False
        self.use_roach_strategy = False
        self.use_hydralisk_strategy = False
        self.booming = True
        self.rushing = False

        # upgrade lists used to perform upgrades in a particular order
        self.evolution_chamber_upgrades = roundrobin(
            ZERG_MELEE_WEAPON_UPGRADES, ZERG_GROUND_ARMOR_UPGRADES) + ZERG_RANGED_WEAPON_UPGRADES
        self.spire_upgrades = roundrobin(
            ZERG_FLYING_WEAPON_UPGRADES, ZERG_FLYING_ARMOR_UPGRADES)
        self.ultralisk_cavern_upgrades = ULTRALISK_DEN_ABILITIES

    async def should_build_lair(self):
        return not self.units(UnitTypeId.HIVE) and self.can_afford(UnitTypeId.LAIR) and await self.can_cast(self.townhalls.first, AbilityId.UPGRADETOLAIR_LAIR)

    def should_build_hive(self):
        return self.units(UnitTypeId.INFESTATIONPIT).ready.exists and not self.units(
            UnitTypeId.HIVE).ready.exists and not self.already_pending(UnitTypeId.HIVE) and self.can_afford(UnitTypeId.HIVE)

    def should_build_spire(self):
        return self.use_mutalisk_strategy and not self.units(
            UnitTypeId.SPIRE).ready.exists and not self.already_pending(UnitTypeId.SPIRE)

    async def can_build_expansion(self):
        return await self.get_next_expansion() and self.can_afford(UnitTypeId.HATCHERY)

    def should_build_expansion(self):
        if self.state.score.collection_rate_minerals < 600 and self.time > 200:
            return True
        # get_forces(self).ready.amount > 10
        return not self.already_pending(UnitTypeId.HATCHERY) and self.time - self.last_expansion_time > 10 and (self.expansion_count < 1 or (self.booming and self.time > 400))

    async def on_game_step(self, iteration):
        # print('LOST ARMY: {} KILLED ARMY: {} MINERALS GAINED PER SECOND: {}'.format(
        #     self.state.score.lost_minerals_army, self.state.score.killed_minerals_army, self.state.score.collection_rate_minerals))
        if self.already_pending(UnitTypeId.LAIR) or self.already_pending(UnitTypeId.HIVE):
            print('lair pending: {} hive pending: {}'.format(self.already_pending(
                UnitTypeId.LAIR), self.already_pending(UnitTypeId.HIVE)))
        townhalls_under_attack = self.get_townhalls_under_attack()
        is_under_attack = townhalls_under_attack.amount > 0
        if is_under_attack:
            self.last_defensive_situation_time = self.time
        if iteration % 8 == 0:
            self.manage_strategies()
        has_been_under_attack_recently = self.get_has_been_under_attack_recently(
            is_under_attack=is_under_attack)

        # we're losing, go for broke.
        if not self.townhalls.exists:
            target = self.select_target()
            if iteration % 50 == 0:
                actions = []
                for unit in self.workers | self.units(UnitTypeId.QUEEN) | get_forces(self):
                    actions.append(unit.attack(target))
                await self.do_actions(actions)
            return

        if iteration % 50 == 0:
            await self.distribute_workers()
            await self.set_rally_points()

        await self.improve_military_tech()

        if not has_been_under_attack_recently and self.should_build_gas():
            await self.build_gas()

        if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and iteration % 50 == 0:
            if not self.units(UnitTypeId.LAIR).ready.exists and self.townhalls.first:
                if await self.should_build_lair():
                    if not self.units(UnitTypeId.LAIR).ready.exists and not already_researching_lair(self):
                        bot_logger.log_action(self, "building lair")
                        await self.do(self.townhalls.ready.first.build(UnitTypeId.LAIR))
            elif self.should_build_spire():
                bot_logger.log_action(self, "building spire")
                await self.build(UnitTypeId.SPIRE, near=self.start_location)

            if self.should_build_hive():
                lair = self.units(UnitTypeId.LAIR).ready.noqueue.exists and self.units(UnitTypeId.LAIR).ready.noqueue.closest_to(
                    self.start_location)
                if lair and not already_researching_hive(self):
                    bot_logger.log_action(self, "building hive")
                    await self.do(lair.build(UnitTypeId.HIVE))

        if not (is_under_attack or has_been_under_attack_recently) and self.should_build_drones():
            await self.build_drones()
        await self.build_units(iteration, is_under_attack=is_under_attack)

        for queen in self.units(UnitTypeId.QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.do(queen(AbilityId.EFFECT_INJECTLARVA, self.townhalls.closest_to(queen)))
        townhall_count = self.townhalls.ready.amount
        if townhall_count < 3 or self.time > 500 and not has_been_under_attack_recently and get_workers_per_townhall(self) > 14:
            if self.should_build_expansion():
                if await self.can_build_expansion():
                    self.expansion_count += 1
                    self.last_expansion_time = self.time
                    bot_logger.log_action(
                        self, "taking expansion #{} at time: {} with {} workers per hatchery".format(self.expansion_count, self.time, get_workers_per_townhall(self)))
                    await self.expand_now(max_distance=5)

        await self.micro_army(iteration=iteration, is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)

    def get_rally_point(self):
        return self.game_info.map_center if self.rushing else self.townhalls.center.towards(self.game_info.map_center, 25)

    def rally_building(self, building, rally_point=None):
        return self.do(building(AbilityId.RALLY_BUILDING, rally_point if rally_point else self.get_rally_point()))

    async def set_rally_points(self):
        bot_logger.log_action(self, 'setting rally points')
        rally_units = AbilityId.RALLY_HATCHERY_UNITS
        rally_workers = AbilityId.RALLY_HATCHERY_WORKERS
        rally_point = self.get_rally_point()
        actions = []
        for townhall in self.townhalls.ready:
            actions.append(townhall(rally_units, rally_point))
            actions.append(
                townhall(rally_workers, self.state.mineral_field.closest_to(townhall)))
        await self.do_actions(actions)

    async def micro_army(self, iteration=None, is_under_attack=False, townhalls_under_attack=[]):
        actions = [
            *self.micro_idle(is_under_attack=is_under_attack),
            *self.micro_drones(is_under_attack=is_under_attack,
                               townhalls_under_attack=townhalls_under_attack),
            *self.micro_zerglings(is_under_attack=is_under_attack,
                                  townhalls_under_attack=townhalls_under_attack),
            *self.micro_roaches(is_under_attack=is_under_attack,
                                townhalls_under_attack=townhalls_under_attack),
            *self.micro_hydralisks(is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack),
            *self.micro_mutalisks(is_under_attack=is_under_attack,
                                  townhalls_under_attack=townhalls_under_attack),
            *self.micro_ultralisks(is_under_attack=is_under_attack,
                                   townhalls_under_attack=townhalls_under_attack),
            *self.micro_overlords(iteration)
        ]
        await self.do_actions(actions)

    def micro_idle(self, is_under_attack=False) -> List[UnitCommand]:
        actions = []
        target = self.get_rally_point()
        for unit in get_forces(self).idle.further_than(10, target):
            actions.append(unit.move(target))
        return actions

    def micro_military_unit(self, unit: Unit, is_under_attack: bool=False, townhalls_under_attack=[]):
        is_threat = get_is_threat_callable(unit)
        is_targettable = get_is_targettable_callable(unit)

        def is_targettable_threat(u: Unit) -> bool: return is_threat(
            u) and is_targettable(u)
        targettable_threats_to_this_unit = get_enemies_near_position(
            self, unit, unit_filter=is_targettable_threat
        )
        # attack threats to this unit
        if targettable_threats_to_this_unit.exists:
            closest_enemy = targettable_threats_to_this_unit.closest_to(unit)
            return unit.attack(closest_enemy)
        # attack units attacking the closest townhall
        if townhalls_under_attack:
            return unit.attack(self.known_enemy_units.closest_to(townhalls_under_attack.filter(is_targettable).closest_to(unit)))
        enemy_targets = get_enemies_near_position(
            self, unit, unit_filter=is_targettable)
        # attack nearby units
        if enemy_targets.exists:
            closest_target = enemy_targets.closest_to(unit)
            weapon_range = max(unit.ground_range, unit.air_range)
            if weapon_range > 3:
                if unit.weapon_cooldown == 0:
                    return unit.attack(closest_target)
                elif closest_target.distance_to(unit) > weapon_range / 2 and unit.health_percentage > .33:
                    unit.move(closest_target)
            else:
                return unit.attack(closest_target)
        # we're under attack do something?
        # ? TODO is this redundant with townhalls_under_attack?
        elif is_under_attack:
            target = self.select_target()
            return unit.move(target)
        elif (self.state.score.used_minerals_army + (self.state.score.used_vespene_army * 2) > 4000 and self.rushing) or self.supply_used > 190:
            target = self.select_target()
            return unit.move(target)

    def micro_drones(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        actions = []
        if is_under_attack:
            # pull drones from hatcheries that are under attack
            for townhall in townhalls_under_attack:
                is_main = townhall.distance_to(self.start_location) < 10
                drones = self.units(
                    UnitTypeId.DRONE).closer_than(20, townhall)
                if drones.exists:
                    for drone in drones:
                        if not is_main:
                            actions.append(drone.move(self.start_location))
        return actions

    def micro_zerglings(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        unit_id = UnitTypeId.ZERGLING
        zerglings = self.units(unit_id).ready
        actions = []
        for zergling in zerglings:
            action = self.micro_military_unit(
                zergling, is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)
            if action:
                actions.append(action)
        return actions

    def micro_roaches(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        unit_id = UnitTypeId.ROACH
        roaches = self.units(unit_id).ready
        actions = []
        for roach in roaches:
            action = self.micro_military_unit(
                roach, is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)
            if action:
                actions.append(action)
        return actions

    def micro_hydralisks(self, is_under_attack: bool=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        unit_id = UnitTypeId.HYDRALISK
        hydralisks = self.units(unit_id).ready
        actions = []
        for hydralisk in hydralisks:
            action = self.micro_military_unit(hydralisk, is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)
            if action:
                actions.append(action)
        return actions

    def micro_mutalisks(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        unit_id = UnitTypeId.MUTALISK
        mutalisks = self.units(unit_id).ready
        actions = []
        for mutalisk in mutalisks:
            if mutalisk.health_percentage < .33:
                actions.append(mutalisk.move(self.start_location))
                continue
            action = self.micro_military_unit(
                mutalisk, is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)
            if action:
                actions.append(action)
        return actions

    def micro_ultralisks(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        unit_id = UnitTypeId.ULTRALISK
        ultralisks = self.units(unit_id).ready
        actions = []
        for ultralisk in ultralisks:
            if ultralisk.health_percentage < .33:
                actions.append(ultralisk.move(self.start_location))
                continue
            action = self.micro_military_unit(
                ultralisk, is_under_attack=is_under_attack, townhalls_under_attack=townhalls_under_attack)
            if action:
                actions.append(action)
        return actions

    def micro_overlords(self, iteration, be_cowardly=True, spread_creep=True, spread_out=True) -> List[UnitCommand]:
        unit_id = UnitTypeId.OVERLORD
        overlords = self.units(unit_id).ready
        actions = []
        if spread_creep and iteration % 50 == 0 and self.units(UnitTypeId.LAIR).ready.exists or self.units(UnitTypeId.HIVE).ready.exists:
            for overlord in overlords:
                actions.append(overlord(AbilityId.BEHAVIOR_GENERATECREEPON))
        if spread_out:
            if iteration % 10 == 0 and self.time % 60 < 1 and self.time > 300:
                for townhall in self.townhalls.ready:
                    for overlord in self.units(unit_id).ready.idle.closer_than(10, townhall):
                        actions.append(overlord.move(
                            self.state.mineral_field.further_than(40, self.enemy_start_locations[0]).random))
            if iteration % 50 == 0:
                for overlord in self.units(unit_id).filter(lambda u: self.units(unit_id).closer_than(10, u).amount >= 2).ready:
                    actions.append(overlord.move(
                        self.state.mineral_field.further_than(40, self.enemy_start_locations[0]).random))
        if be_cowardly:
            for overlord in overlords:
                enemy_threats = get_enemies_near_position(
                    self, overlord, 10, unit_filter=lambda u: u.can_attack_air)
                if enemy_threats.exists:
                    closest_threat = enemy_threats.closest_to(overlord)
                    away_from_threat = closest_threat.position.towards(
                        self.start_location, distance=closest_threat.sight_range)
                    actions.append(overlord.move(away_from_threat))
        return actions

    async def first_iteration(self):
        await self.distribute_workers()
        await self.scout_enemy()

    def select_target(self):
        """select a general priority target"""
        if self.known_enemy_structures.exists:
            return self.known_enemy_structures.closest_to(self.start_location)
        if self.time < 400:
            target = self.enemy_start_locations[0].closest(
                self.potential_enemy_expansions)
            return target
        return self.enemy_start_locations[0]

    async def scout_enemy(self):
        scout = self.workers.random if self.time < 200 else self.units(
            UnitTypeId.ZERGLING).idle.random
        action_list = []
        start_location = random.choice(self.enemy_start_locations)
        for _ in range(100):
            position = start_location.towards_with_random_angle(
                self.game_info.map_center, random.randrange(1, 20))
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

    async def handle_ultralisk_cavern_upgrades(self):
        for ultralisk_cavern in self.units(UnitTypeId.ULTRALISKCAVERN).ready.noqueue:
            for upgrade in self.ultralisk_cavern_upgrades:
                if self.can_afford(upgrade):
                    result = await self.do(ultralisk_cavern(upgrade))
                    if result:
                        return
                    bot_logger.log_action(
                        self, 'buying upgrade {}'.format(upgrade))
            # TODO figure out why this errors
            # available_abilities = await self.get_available_abilities(ultralisk_cavern)
            # print(available_abilities)
                # if upgrade in available_abilities:

    async def upgrade_military(self):
        if not self.metabolic_boost_started:
            started_upgrade = await upgrade_zergling_speed(self)
            if started_upgrade:
                self.metabolic_boost_started = True
        if not self.burrow_started and not self.already_pending_upgrade(UpgradeId.BURROW):
            if self.townhalls.ready.noqueue.exists:
                self.burrow_started = True
                await self.do(self.townhalls.ready.noqueue.closest_to(self.start_location).research(UpgradeId.BURROW))

        await self.handle_evo_chamber_upgrades()
        if self.use_mutalisk_strategy:
            await self.handle_spire_upgrades()
        if self.use_ultralisk_strategy:
            await self.handle_ultralisk_cavern_upgrades()

    def should_build_infestation_pit(self) -> bool:
        return self.supply_used > 100 and not self.units(UnitTypeId.INFESTATIONPIT).ready.exists and self.can_afford(UnitTypeId.INFESTATIONPIT) and not self.already_pending(UnitTypeId.INFESTATIONPIT) and self.units(UnitTypeId.SPIRE).ready.exists

    def should_build_ultralisk_den(self) -> bool:
        return self.use_ultralisk_strategy and not self.units(UnitTypeId.ULTRALISKCAVERN) and not self.already_pending(UnitTypeId.ULTRALISKCAVERN) and self.can_afford(UnitTypeId.ULTRALISKCAVERN)

    def should_check_if_should_research_adrenal_glands(self) -> bool:
        return self.units(UnitTypeId.SPAWNINGPOOL).ready.noqueue.exists and self.can_afford(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS)

    def should_build_evolution_chamber(self) -> bool:
        return self.expansion_count > 1 and not self.units(UnitTypeId.EVOLUTIONCHAMBER).amount >= 2 and self.can_afford(UnitTypeId.EVOLUTIONCHAMBER) and not self.already_pending(UnitTypeId.EVOLUTIONCHAMBER)

    def should_build_roach_warren(self) -> bool:
        return self.use_roach_strategy and not self.units(UnitTypeId.ROACHWARREN).ready.exists and self.can_afford(UnitTypeId.ROACHWARREN) and not self.already_pending(UnitTypeId.ROACHWARREN)

    def should_build_hydralisk_den(self) -> bool:
        return self.use_hydralisk_strategy and not self.units(UnitTypeId.HYDRALISKDEN).ready.exists and self.can_afford(UnitTypeId.HYDRALISKDEN) and not self.already_pending(UnitTypeId.HYDRALISKDEN)

    async def build_once_in_base(self, building: UnitTypeId, min_distance=7, max_distance=15):
        if not self.townhalls.exists:
            return
        base_location = self.start_location if self.is_visible(
            self.start_location) else self.townhalls.random.position
        location_near_base = base_location.towards_with_random_angle(
            self.game_info.map_center, random.randrange(min_distance, max_distance))
        await build_building_once(self, building, location_near_base)

    async def improve_military_tech(self):
        if self.expansion_count > 0:
            await self.build_once_in_base(UnitTypeId.SPAWNINGPOOL)
        if self.should_build_roach_warren():
            await self.build_once_in_base(UnitTypeId.ROACHWARREN)
        if self.should_build_hydralisk_den():
            await self.build_once_in_base(UnitTypeId.HYDRALISKDEN)
        if self.should_build_infestation_pit():
            await self.build_once_in_base(UnitTypeId.INFESTATIONPIT)
        if self.units(UnitTypeId.HIVE).ready.exists:
            if self.should_build_ultralisk_den():
                await self.build_once_in_base(UnitTypeId.ULTRALISKCAVERN)
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

    def should_build_overlord(self) -> bool:
        return (self.supply_left < 4 or self.minerals > 1500) and not self.already_pending(
            UnitTypeId.OVERLORD) and not self.supply_cap == 200

    def should_build_ultralisk(self) -> bool:
        return self.use_ultralisk_strategy and self.can_afford(UnitTypeId.ULTRALISK) and self.units(UnitTypeId.ULTRALISKCAVERN).ready.exists

    def should_build_mutalisk(self) -> bool:
        return self.use_mutalisk_strategy and self.can_afford(UnitTypeId.MUTALISK) and self.units(UnitTypeId.SPIRE).ready.exists

    def should_build_hydralisk(self) -> bool:
        return self.use_hydralisk_strategy and self.can_afford(
            UnitTypeId.HYDRALISK) and self.units(UnitTypeId.HYDRALISKDEN).ready.exists
    
    def should_build_roach(self) -> bool:
        return self.use_roach_strategy and self.can_afford(UnitTypeId.ROACH) and self.units(UnitTypeId.ROACHWARREN).ready.exists

    def should_build_zergling(self) -> bool:
        return self.vespene < 100 or self.minerals / self.vespene > .3

    async def build_units(self, iteration, is_under_attack=False):
        if iteration % 50:
            # build queens
            for townhall in self.townhalls.ready.noqueue:
                if self.units(UnitTypeId.QUEEN).ready.closer_than(5, townhall).amount < 1:
                    if self.can_afford(UnitTypeId.QUEEN) and self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and not self.already_pending(UnitTypeId.QUEEN):
                        bot_logger.log_action(self, 'building queen')
                        await self.do(townhall.train(UnitTypeId.QUEEN))
        if self.units(UnitTypeId.LARVA).amount <= 0:
            return

        if self.should_build_overlord():
            overlords_to_build = 1
            if self.time > 200:
                overlords_to_build += 1
            if self.time > 400:
                overlords_to_build += 1
            for _ in range(overlords_to_build):
                await build_overlord(self, None)

        for larva in self.units(UnitTypeId.LARVA).ready:
            if self.supply_left < 0:
                return
            # TODO generate these weights more dynamically
            ultralisk_weight = .8
            mutalisk_weight = .8
            hydralisk_weight = .8
            roach_weight = .4
            zergling_weight = .7
            if self.should_build_ultralisk() and random.random() > ultralisk_weight:
                bot_logger.log_action(self, "building ultralisk")
                await self.do(larva.train(
                    UnitTypeId.ULTRALISK
                ))
            elif self.should_build_mutalisk() and random.random() > mutalisk_weight:
                bot_logger.log_action(self, "building mutalisk")
                await self.do(larva.train(
                    UnitTypeId.MUTALISK))
            elif self.should_build_hydralisk() and random.random() > hydralisk_weight:
                bot_logger.log_action(self, "building hydralisk")
                await self.do(larva.train(UnitTypeId.HYDRALISK))
            elif self.should_build_roach() and random.random() > roach_weight:
                bot_logger.log_action(self, "building roach")
                await self.do(larva.train(UnitTypeId.ROACH))
            elif self.should_build_zergling() and random.random() > zergling_weight:
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
