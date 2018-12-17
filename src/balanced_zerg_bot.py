import random
import sc2
import math
from sc2 import Result
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2, Point3
from sc2.constants import AbilityId, BuffId, UnitTypeId, UpgradeId
from sc2.unit_command import UnitCommand
from typing import List, Callable, Optional, Dict, Union

import src.bot_logger as bot_logger
from src.helpers import roundrobin, between, value_between_any, property_cache_forever, \
get_figure_name, get_plot_directory, make_dir_if_not_exists
from src.bot_actions import build_building_once, get_workers_per_townhall, get_enemies_near_position, \
find_potential_enemy_expansions, get_is_targettable_callable, get_is_threat_callable, get_closest_to
from src.zerg_actions import get_random_larva, build_drone, build_zergling, build_overlord, \
    upgrade_zergling_speed, get_forces, geyser_has_extractor, already_researching_lair, \
    already_researching_hive, ZERG_MELEE_WEAPON_UPGRADES, ZERG_RANGED_WEAPON_UPGRADES, \
    ZERG_GROUND_ARMOR_UPGRADES, ZERG_FLYING_WEAPON_UPGRADES, ZERG_FLYING_ARMOR_UPGRADES, \
    ULTRALISK_CAVERN_ABILITIES, ROACHWARREN_ABILITIES, HYDRALISK_DEN_ABILITIES
from src.zerg_bot_base import ZergBotBase
from src.location_picker import LocationPicker
from src.location_checker import LocationChecker
from src.bot_plotter import BotPlotter
from src.types import Location


class BalancedZergBot(ZergBotBase):
    def __init__(self,
        auto_camera=True,
        should_show_plot=True,
        # TODO make class wrapper for timings
        boom_timings=[
            (-1, 500),
            (550, 775),
            (800, 1000),
            (1500, 1900),
            (2000, math.inf)
        ],
        rush_timings=[
            (400, 850),
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
            (300, 800),
            (900, 1200)
        ],
        ultralisk_timings=[
            (400, math.inf)
        ],
        roach_timings=[
            (400, 700),
            (1000, math.inf)
        ],
        hydralisk_timings=[
            (600, math.inf)
        ]
    ):
        super().__init__()
        self.auto_camera = auto_camera
        self.boom_timings = boom_timings
        self.rush_timings = rush_timings
        self.mutalisk_timings = mutalisk_timings
        self.ultralisk_timings = ultralisk_timings
        self.roach_timings = roach_timings
        self.hydralisk_timings = hydralisk_timings
        self.should_show_plot = should_show_plot
        if self.should_show_plot:
            self.plotter = BotPlotter({
                'mpm': [
                    (([], [], 'c-'), {'label': 'Minerals per minute'})
                ],
                'gpm': [
                    (([], [], 'g-'), {'label': 'Gas per minute'})
                ],
                'supply_used': [
                    (([], [], 'k-'), {'label': 'Supply used'}),
                    (([], [], 'g-'), {'label': 'Workers'}),
                    (([], [], 'b-'), {'label': 'Forces'})
                ],
                'army_value_balance': [
                    (([], [], 'r-'), {'label': 'Army value lost'}),
                    (([], [], 'b-'), {'label': 'Army value killed'})
                ],
            })

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
        military_value_lost = self.state.score.lost_minerals_army + self.state.score.lost_vespene_army
        military_value_killed = self.state.score.killed_minerals_army + self.state.score.killed_vespene_army
        return (military_value_lost < military_value_killed) or self._is_rushing_time

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
        if unit.type_id is UnitTypeId.OVERLORD:
            await self.do(unit.move(self.state.mineral_field.further_than(10, self.enemy_start_locations[0]).random))

    async def on_building_construction_complete(self, unit: Unit):
        if unit.type_id is UnitTypeId.EXTRACTOR:
            await self.distribute_workers()

    def get_townhalls_under_attack(self) -> Units:
        return self.townhalls.filter(lambda townhall: get_enemies_near_position(bot=self, position=townhall, distance=35, unit_filter=lambda u: u.can_attack_ground and u.ground_dps > 5).amount > 3)

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

    def on_start(self):
        # settings
        self.max_worker_count = 85
        self.ideal_workers_per_hatch = 24

        # milestones
        self.metabolic_boost_started = False
        self.adrenal_glands_started = False
        self.burrow_started = False

        # event memories
        self.expansion_count = 0
        self.last_expansion_time = 0
        self.last_defensive_situation_time = None
        # add self.expansion_locations to this list
        location_options = {}
        for i, location in enumerate(self.enemy_start_locations):
            location_options[str(i)] = location
        self.checked_enemy_start_locations = LocationPicker(self, location_options=location_options, location_checker=lambda bot, location: bot.units.closer_than(20, location).amount > 10)

        # graphing
        if self.should_show_plot:
            self._time_history = []
            self._minerals_per_minute_history = []
            self._gas_per_minute_history = []
            self._supply_used_history = []
            self._workers_history = []
            self._forces_history = []
            self._army_value_lost_history = []
            self._army_killed_value_history = []        

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
            ZERG_RANGED_WEAPON_UPGRADES, ZERG_GROUND_ARMOR_UPGRADES, ZERG_MELEE_WEAPON_UPGRADES)
        self.spire_upgrades = roundrobin(
            ZERG_FLYING_WEAPON_UPGRADES, ZERG_FLYING_ARMOR_UPGRADES)
        self.hydralisk_den_upgrades = HYDRALISK_DEN_ABILITIES
        self.roach_warren_upgrades = ROACHWARREN_ABILITIES
        self.ultralisk_cavern_upgrades = ULTRALISK_CAVERN_ABILITIES
    
    async def can_build_lair(self):
        if not self.townhalls.noqueue.exists:
            return False
        return await self.can_cast(self.townhalls.noqueue.closest_to(self.start_location), AbilityId.UPGRADETOLAIR_LAIR) and self.can_afford(UnitTypeId.LAIR)

    def should_build_lair(self):
        return not self.units(UnitTypeId.HIVE) and not self.units(UnitTypeId.LAIR)

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
        return self.time - self.last_expansion_time > 30 and (self.minerals > 500 or self.expansion_count < 1)

    def get_camera_position(self):
        forces = get_forces(self)
        if forces.exists:
            attacking_forces = forces.filter(lambda u: u.is_attacking or get_enemies_near_position(self, u).amount > 5)
            if attacking_forces.exists:
                return attacking_forces.center
            return forces.center
        enemy_units = self.known_enemy_units
        if enemy_units.exists:
            enemy_military_units = enemy_units.filter(lambda u: u.can_attack_ground)
            if enemy_military_units.exists:
                return enemy_military_units.closest_to(self.start_location)
        return self.get_rally_point()

    def update_plot(self):
        self.plotter.plot('mpm', self._time_history, self._minerals_per_minute_history, 'c-', label='Minerals per minute')
        self.plotter.plot('gpm', self._time_history, self._gas_per_minute_history, 'g-', label='Gas per minute')
        self.plotter.plot('supply_used', self._time_history, self._supply_used_history,
                    'k-', label='Supply used')
        self.plotter.plot('supply_used', self._time_history, self._workers_history,
                    'g-', label='Workers')
        self.plotter.plot('supply_used', self._time_history, self._forces_history,
                    'b-', label='Forces')
        self.plotter.plot('army_value_balance', self._time_history, self._army_value_lost_history, 'r-', label='Army value lost')
        self.plotter.plot('army_value_balance', self._time_history,
                          self._army_killed_value_history, 'b-', label='Army value killed')
        self.plotter.show()

    def manage_strategies(self):
        self.manage_booming()
        self.manage_rushing()
        self.manage_roach_strategy()
        self.manage_hydralisk_strategy()
        self.manage_mutalisk_strategy()
        self.manage_ultralisk_strategy()



    async def on_game_step(self, iteration):
        # print('LOST ARMY: {} KILLED ARMY: {} MINERALS GAINED per minute: {}'.format(
        #     self.state.score.lost_minerals_army, self.state.score.killed_minerals_army, self.state.score.collection_rate_minerals))
        if self.already_pending(UnitTypeId.LAIR) or self.already_pending(UnitTypeId.HIVE):
            print('lair pending: {} hive pending: {}'.format(self.already_pending(
                UnitTypeId.LAIR), self.already_pending(UnitTypeId.HIVE)))
        townhalls_under_attack = self.get_townhalls_under_attack()
        is_under_attack = townhalls_under_attack.amount > 0
        has_been_under_attack_recently = self.get_has_been_under_attack_recently(
            is_under_attack=is_under_attack)
        
        # print(checked_start_locations)
        if is_under_attack:
            self.last_defensive_situation_time = self.time
        if iteration % 8 == 0:
            self.manage_strategies()

            if self.should_show_plot:
                # track history of score, etc. (used for graphing only so far)
                self._time_history.append(self.time)
                self._minerals_per_minute_history.append(self.state.score.collection_rate_minerals)
                self._gas_per_minute_history.append(self.state.score.collection_rate_vespene)
                self._supply_used_history.append(self.supply_used)
                self._workers_history.append(self.workers.ready.amount)
                self._forces_history.append(get_forces(self).amount)
                self._army_value_lost_history.append(self.state.score.lost_minerals_army + self.state.score.lost_vespene_army)
                self._army_killed_value_history.append(self.state.score.killed_minerals_army + self.state.score.killed_vespene_army)
                self._time_history = self._time_history[-20:]
                self._workers_history = self._workers_history[-20:]
                self._forces_history = self._forces_history[-20:]
                self._minerals_per_minute_history = self._minerals_per_minute_history[-20:]
                self._gas_per_minute_history = self._gas_per_minute_history[-20:]
                self._supply_used_history = self._supply_used_history[-20:]
                self._army_value_lost_history = self._army_value_lost_history[-20:]
                self._army_killed_value_history = self._army_killed_value_history[-20:]
                self.update_plot()

        
        # if self.should_show_plot and iteration % 25 == 0:

        if self.auto_camera:
            camera_position = self.get_camera_position()
            if camera_position:
                await self._client.move_camera(camera_position)

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
        await self.build_static_defenses()

        if not has_been_under_attack_recently and self.should_build_gas():
            await self.build_gas()

        if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and iteration % 10 == 0:
            if not self.units(UnitTypeId.LAIR).ready.exists and self.townhalls.first:
                if self.should_build_lair():
                    if await self.can_build_lair() and not already_researching_lair(self):
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

        if self.supply_left > 0:
            await self.build_military_units()
            if not (is_under_attack or has_been_under_attack_recently) and self.should_build_drones():
                if self.can_build_drone():
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
        if self.rushing:
            return self.game_info.map_center
        if self.townhalls.exists:
            return self.townhalls.center.towards(self.game_info.map_center, 25)
        return self.start_location

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

    async def build_static_defenses(self):
        spawning_pools = self.units(UnitTypeId.SPAWNINGPOOL)
        if not spawning_pools.ready.exists:
            return
        spine_crawlers = self.units(UnitTypeId.SPINECRAWLER)
        spore_crawlers = self.units(UnitTypeId.SPORECRAWLER)
        ideal_spine_crawlers_per_base = 0
        ideal_spore_crawlers_per_base = 0
        if self.time > 250:
            ideal_spine_crawlers_per_base += 1
        if self.time > 350:
            ideal_spine_crawlers_per_base += 1
        if self.time > 400:
            ideal_spore_crawlers_per_base += 1
        
        #     ideal_spine_crawlers_per_base += 1
        # if self.time > 500:
        #     ideal_spine_crawlers_per_base += 1
        # if self.time > 1000:
        #     ideal_spine_crawlers_per_base += 1
        #     ideal_spore_crawlers_per_base += 1

        if ideal_spine_crawlers_per_base > 0 or ideal_spore_crawlers_per_base > 0:
            townhalls = self.townhalls.ready
            if townhalls.exists:
                townhall = townhalls.closest_to(self.enemy_start_locations[0])
                if spine_crawlers.closer_than(20, townhall).ready.amount < ideal_spine_crawlers_per_base and not self.already_pending(UnitTypeId.SPINECRAWLER) and self.can_afford(UnitTypeId.SPINECRAWLER):
                    await self.build(UnitTypeId.SPINECRAWLER, near=townhall.position.towards_with_random_angle(self.game_info.map_center, distance=10))
                if spore_crawlers.closer_than(20, townhall).ready.amount < ideal_spore_crawlers_per_base and not self.already_pending(UnitTypeId.SPORECRAWLER) and self.can_afford(UnitTypeId.SPORECRAWLER):
                    await self.build(UnitTypeId.SPORECRAWLER, near=townhall)

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
            actions.append(unit.attack(target))
        return actions

    def _micro_military_unit_with_target(self, unit: Unit, target) -> Optional[UnitCommand]:
        weapon_range = max(unit.ground_range, unit.air_range)
        if unit.health_percentage < .33:
            forces = get_forces(self)
            # TODO improve. Maybe only do this if the unit is in range of an enemy
            return unit.move(target.position.towards(
                forces.center if forces.exists else self.start_location, weapon_range))
        if weapon_range > 3:
            if unit.weapon_cooldown == 0:
                return unit.attack(target)
            if unit.health_percentage > .33 and target.distance_to(unit) > weapon_range * .7:
                # TODO improve. Units move towards target a bit too much.
                return unit.move(target)
        else:
            return unit.attack(target)

    def micro_military_unit(self, unit: Unit, is_under_attack: bool=False, townhalls_under_attack=[]) -> Optional[UnitCommand]:
        #   for effect in self.state.effects:
        #     if effect.id == EffectId.RAVAGERCORROSIVEBILECP:
        #         positions = effect.positions
        #         # dodge the ravager biles

        is_threat = get_is_threat_callable(unit)

        is_targettable = get_is_targettable_callable(unit)
        
        targettable_units = get_enemies_near_position(
            self, unit, unit_filter=is_targettable
        )
        weapon_range = max(unit.ground_range, unit.air_range)
        targettable_units_in_range = targettable_units.closer_than(weapon_range, unit)
        targettable_threats = targettable_units.filter(is_threat)
        # prioritize targettable threats to this unit
        if targettable_threats.exists:
            # attack low health threats in range first
            low_health_threats_in_range = targettable_threats.closer_than(weapon_range, unit).filter(lambda u: u.health_percentage < .5)
            if low_health_threats_in_range.exists:
                lowest_health_threat_in_range = low_health_threats_in_range.sorted(lambda u: u.health_percentage).first
                action = self._micro_military_unit_with_target(unit, lowest_health_threat_in_range)
                if action:
                    return action

            # otherwise the closest threat first
            closest_threat = targettable_threats.closest_to(unit)
            action = self._micro_military_unit_with_target(unit, closest_threat)
            if action:
                return action

        # then target low health units in range
        if targettable_units_in_range.exists:
            
            lowest_health = targettable_units_in_range.sorted(lambda u: u.health_percentage and u.can_attack_ground or u.can_attack_air).first
            if lowest_health.health_percentage < .8:
                action = self._micro_military_unit_with_target(unit, lowest_health)
                if action:
                    return action

        # then attack any targettable unit nearby
        if targettable_units.exists:
            closest = targettable_units.closest_to(unit)
            action = self._micro_military_unit_with_target(unit, closest)
            if action:
                return action

        # then attack closest unit attacking one of our bases
        if townhalls_under_attack:
            return unit.attack(self.known_enemy_units.closest_to(townhalls_under_attack.filter(is_targettable).closest_to(unit)))
        # perform a rush or timing
        elif self.rushing or self.supply_used > 190:
            all_forces = get_forces(self)
            friendly_forces_nearby = all_forces.closer_than(15, unit)
            target = self.select_target()
            # TODO improve. Units sometimes still run in without enough aid.
            # if has backup attack
            if friendly_forces_nearby.exists and friendly_forces_nearby.amount > all_forces.amount * .75:
                return unit.attack(target)
            # group up
            elif all_forces.exists:
                return unit.move(all_forces.center.towards(target, 15))

    def micro_drones(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        actions = []
        for drone in self.workers.returning.further_than(10, self.start_location).filter(lambda d: get_enemies_near_position(self, d, distance=30).amount > 5):
            actions.append(drone.move(self.start_location))
        if is_under_attack:
            # pull drones from hatcheries that are under attack
            for townhall in townhalls_under_attack:
                is_main = townhall.distance_to(self.start_location) < 10
                should_pull_drones = get_enemies_near_position(
                    bot=self, position=townhall, distance=10, unit_filter=lambda u: u.can_attack_ground and u.ground_dps > 5).amount > 5
                if should_pull_drones:
                    drones = self.units(
                        UnitTypeId.DRONE).closer_than(20, townhall)
                    if drones.exists and drones.filter(lambda d: d.health_percentage < .5).exists:
                        for drone in drones:
                            if not is_main:
                                actions.append(drone.move(self.start_location))
        return actions

    def micro_zerglings(self, is_under_attack=False, townhalls_under_attack=[]) -> List[UnitCommand]:
        # TODO desperately needs to be improved.
        # After early game, zerglings just pour in to die by the hundreds
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
        for burrowed_roach in self.units(UnitTypeId.ROACHBURROWED).ready:
            if burrowed_roach.health_percentage > .50:
                actions.append(burrowed_roach(AbilityId.BURROWUP_ROACH))
            else:
                actions.append(burrowed_roach.move(self.start_location))
        for roach in roaches:
            if self.burrow_started and not self.already_pending_upgrade(UpgradeId.BURROW) and roach.health_percentage < .33:
                    actions.append(roach(AbilityId.BURROWDOWN_ROACH))
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
        forces = get_forces(self)
        for mutalisk in mutalisks:
            
            # retreat if low health or outnumbered
            if mutalisk.health_percentage < .40:
                nearby_forces = forces.closer_than(20, mutalisk)
                nearby_threats = get_enemies_near_position(
                    self, mutalisk, distance=20, unit_filter=get_is_threat_callable(mutalisk))
                should_retreat = nearby_forces.amount < nearby_threats.amount
                has_forces = forces.amount > 10
                if should_retreat:
                    retreat_distance = mutalisk.ground_range if has_forces else mutalisk.ground_range * 3
                    retreat_position = mutalisk.position.towards(
                        forces.center if has_forces else self.start_location, retreat_distance)
                    if mutalisk.distance_to(retreat_position) > retreat_distance / 2:
                        actions.append(mutalisk.move(retreat_position))
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
        for burrowed_ultralisk in self.units(UnitTypeId.ULTRALISKBURROWED).ready:
            if burrowed_ultralisk.health_percentage > .50:
                actions.append(burrowed_ultralisk(AbilityId.BURROWUP_ULTRALISK))
        for ultralisk in ultralisks:
            if ultralisk.health_percentage < .33:
                if self.burrow_started and not self.already_pending_upgrade(UpgradeId.BURROW):
                    actions.append(ultralisk(AbilityId.BURROWDOWN_ULTRALISK))
                else:
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
            distance = 35
            if iteration % 8 == 0 and self.time % 60 == 0:
                for overlord in overlords.idle:
                    location = self.start_location.towards_with_random_angle(self.enemy_start_locations[0], distance=distance)
                    actions.append(overlord.move(location))
                    distance += 15
        if be_cowardly:
            for overlord in overlords:
                enemy_threats = get_enemies_near_position(
                    self, overlord, 20, unit_filter=lambda u: u.can_attack_air)
                if enemy_threats.exists:
                    closest_threat = enemy_threats.closest_to(overlord)
                    away_from_threat = closest_threat.position.towards(
                        self.start_location, distance=closest_threat.sight_range + 10)
                    actions.append(overlord.move(away_from_threat))
        return actions

    async def first_iteration(self):
        await self.distribute_workers()
        await self.scout_enemy()

    def get_checked_locations(self) -> Location:
        """Finds locations that haven't met the location_checkers defined in """
        return list(map(lambda item: item[1].location,
                        self.checked_enemy_start_locations.get_inactive().items()))

    def get_closest_checked_location_to_start_location(self):
        locations = self.get_checked_locations()
        return self.get_closest_to_start_location(locations)

    def get_closest_to_start_location(self, locations: List[Location]) -> Optional[Location]:
        start_location = self.start_location
        return get_closest_to(locations, start_location)


    def select_target(self):
        """select a general priority target"""
        if self.known_enemy_structures.exists:
            return self.known_enemy_structures.closest_to(self.start_location)
        if self.time < 400:
            target = self.enemy_start_locations[0].closest(
                self.potential_enemy_expansions)
            return target
        if self.time < 450:
            return self.enemy_start_locations[0]
        
        return self.get_closest_checked_location_to_start_location()
        # return self.enemy_start_locations[0]

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

    async def handle_roach_warren_upgrades(self):
        for warren in self.units(UnitTypeId.ROACHWARREN).ready.noqueue:
            warren_abilities = await self.get_available_abilities(warren)
            for upgrade in self.roach_warren_upgrades:
                if upgrade in warren_abilities and self.can_afford(upgrade):
                    bot_logger.log_action(self, 'buying upgrade {}'.format(upgrade))
                    await self.do(warren(upgrade))
                    return

    async def handle_hydralisk_den_upgrade(self):
        for den in self.units(UnitTypeId.HYDRALISKDEN).ready.noqueue:
            den_abilities = await self.get_available_abilities(den)
            for upgrade in self.hydralisk_den_upgrades:
                if upgrade in den_abilities and self.can_afford(upgrade):
                    bot_logger.log_action(self, 'buying upgrade {}'.format(upgrade))
                    await self.do(den(upgrade))
                    return

    async def handle_ultralisk_cavern_upgrades(self):
        for ultralisk_cavern in self.units(UnitTypeId.ULTRALISKCAVERN).ready.noqueue:
            cavern_abilities = await self.get_available_abilities(ultralisk_cavern)
            for upgrade in self.ultralisk_cavern_upgrades:
                if upgrade in cavern_abilities and self.can_afford(upgrade):
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
        if not self.burrow_started and not self.already_pending_upgrade(UpgradeId.BURROW) and self.can_afford(UpgradeId.BURROW):
            if self.townhalls.ready.noqueue.exists:
                await self.do(self.townhalls.ready.noqueue.closest_to(self.start_location).research(UpgradeId.BURROW))
                self.burrow_started = True

        await self.handle_evo_chamber_upgrades()
        # TODO: enable this whenever using more spire units
        # if self.use_mutalisk_strategy:
        #     await self.handle_spire_upgrades()
        if self.use_roach_strategy:
            await self.handle_roach_warren_upgrades()
        if self.use_hydralisk_strategy:
            await self.handle_hydralisk_den_upgrade()
        if self.use_ultralisk_strategy:
            await self.handle_ultralisk_cavern_upgrades()

    def should_build_infestation_pit(self) -> bool:
        return self.supply_used > 100 and not self.units(UnitTypeId.INFESTATIONPIT).ready.exists and self.can_afford(UnitTypeId.INFESTATIONPIT) and not self.already_pending(UnitTypeId.INFESTATIONPIT)

    def should_build_ultralisk_den(self) -> bool:
        return self.use_ultralisk_strategy and not self.units(UnitTypeId.ULTRALISKCAVERN).exists and not self.already_pending(UnitTypeId.ULTRALISKCAVERN) and self.can_afford(UnitTypeId.ULTRALISKCAVERN)

    def should_check_if_should_research_adrenal_glands(self) -> bool:
        return self.units(UnitTypeId.SPAWNINGPOOL).ready.noqueue.exists and self.can_afford(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS)

    def should_build_evolution_chamber(self) -> bool:
        ideal_evolution_chamber_amount = 0
        if self.time > 190:
            ideal_evolution_chamber_amount += 1
        if self.time > 300:
            ideal_evolution_chamber_amount += 1

        return self.expansion_count > 1 and self.units(UnitTypeId.EVOLUTIONCHAMBER).amount < ideal_evolution_chamber_amount and self.can_afford(UnitTypeId.EVOLUTIONCHAMBER) and not self.already_pending(UnitTypeId.EVOLUTIONCHAMBER)

    def should_build_roach_warren(self) -> bool:
        return self.use_roach_strategy and self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and not self.units(UnitTypeId.ROACHWARREN).ready.exists and self.can_afford(UnitTypeId.ROACHWARREN) and not self.already_pending(UnitTypeId.ROACHWARREN)

    def should_build_hydralisk_den(self) -> bool:
        return self.use_hydralisk_strategy and (self.units(UnitTypeId.LAIR).ready.exists or self.units(UnitTypeId.HIVE).ready.exists) and not self.units(UnitTypeId.HYDRALISKDEN).ready.exists and self.can_afford(UnitTypeId.HYDRALISKDEN) and not self.already_pending(UnitTypeId.HYDRALISKDEN)

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
        if self.supply_used == 13 and self.time < 60:
            return True
        elif self.supply_used == 19	and self.time < 120:
            return True
        supply_low_amount = 6
        if self.time > 500:
            self.supply_low_amount = 12
        elif self.time > 400:
            self.supply_low_amount = 10
        elif self.time > 250:
            self.supply_low_amount = 8
        return not self.supply_cap == 200 and self.supply_left < supply_low_amount
        # TODO reevaluate what can be used from the comment below
        # return (self.supply_left < max(6, self.units(UnitTypeId.LARVA).ready.amount) or self.minerals > 1500) and not self.already_pending(
        #     UnitTypeId.OVERLORD) and not self.supply_cap == 200

    def should_build_ultralisk(self) -> bool:
        return self.use_ultralisk_strategy and self.can_afford(UnitTypeId.ULTRALISK) and self.units(UnitTypeId.ULTRALISKCAVERN).ready.exists and self.supply_cap >= 6

    def should_build_mutalisk(self) -> bool:
        return self.use_mutalisk_strategy and self.can_afford(UnitTypeId.MUTALISK) and self.units(UnitTypeId.SPIRE).ready.exists and self.supply_left >= 2

    def should_build_hydralisk(self) -> bool:
        return self.use_hydralisk_strategy and self.can_afford(
            UnitTypeId.HYDRALISK) and self.units(UnitTypeId.HYDRALISKDEN).ready.exists and self.supply_left >= 2
    
    def should_build_roach(self) -> bool:
        if self.minerals < 150:
            return False
        return self.use_roach_strategy and self.can_afford(UnitTypeId.ROACH) and self.units(UnitTypeId.ROACHWARREN).ready.exists and self.supply_left >= 2

    def should_build_zergling(self) -> bool:
        # TODO needs work. Zerglings are built instead of any other unit because the bot never gets above 50 minerals
        has_right_mineral_gas_ratio = self.minerals / self.vespene > 1.3 if self.vespene else True
        # not self.state.score.lost_minerals_army + self.state.score.lost_vespene_army > 1200
        return self.get_has_been_under_attack_recently() or (not self.booming and has_right_mineral_gas_ratio)

    def calculate_minerals_after_seconds(self, seconds_from_now) -> int:
        return self.minerals + (seconds_from_now * self.state.score.collection_rate_minerals)

    # TODO needs work, still returning too many overlords
    def get_overlords_needed(self) -> int:
            """Calculates the number of overlords to make given the current situation.
                https://gamefaqs.gamespot.com/boards/939643-starcraft-ii-wings-of-liberty/58543769
                > You should get about 6 or 7 larva per hatchery between every queen inject.
                > Overlords take less time to build than it takes from inject to extra larva
                > If you're going lings, 1 larva = 1 supply.
                > If you're going roach, hydra, muta, 1 larva = 2 supply.
                > Overlords give 8 supply.

                Therefore,

                If you're making lings, you can make 1 overlord per 7 larva and still have 
                enough space to make a queen during that period (common).

                If you're making 2 food units, you'll probably want to make 2 overlords per 7 larva 
                (again, an inject period), and maybe 1 overlord per round every 3rd time.
            """
            larvae = self.units(UnitTypeId.LARVA).ready
            queen_ready_to_inject_count = self.units(UnitTypeId.QUEEN).ready.filter(lambda q: q.energy >= 25).amount
            maximum_future_larva_count = self.townhalls.amount + (queen_ready_to_inject_count * 7)
            current_larva_count = larvae.amount
            supply_cap = 200
            supply_used = self.supply_used
            maximum_supply_needed = supply_cap - supply_used
            supply_per_overlord = 8
            maximum_overlords_needed = round(
                maximum_supply_needed / supply_per_overlord)
            overlords_in_progress = self.units(UnitTypeId.OVERLORD).not_ready().amount
            overlord_build_time = 18
            minimum_unit_cost = 50
            minerals_pending = self.calculate_minerals_after_seconds(overlord_build_time / 3)
            max_units_buildable = round(minerals_pending / minimum_unit_cost)
            larva_to_account_for = maximum_future_larva_count + current_larva_count
            supply_per_larva = 1
            if self.use_ultralisk_strategy:
                supply_per_larva = 6
            if self.use_roach_strategy or self.use_mutalisk_strategy or self.use_hydralisk_strategy:
                supply_per_larva = 2
            # TODO / 2 is just to lower the production rate a little bit. This might not be necessary
            supply_demand = (larva_to_account_for * supply_per_larva)
            overlords_to_meet_demand = min(round(supply_demand / supply_per_overlord), max_units_buildable)
            return max(min(maximum_overlords_needed, overlords_to_meet_demand, ) - overlords_in_progress, 0)


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
            overlords_to_build = self.get_overlords_needed()
            if overlords_to_build > 1:
                await build_overlord(self, None)

            # for _ in range(overlords_to_build):

        # ! THIS IS BROKEN !
        # maybe this shouldn't be a loop
        # for larva in self.units(UnitTypeId.LARVA).ready:
        #     if self.supply_left < 0:
        #         return
        #     # TODO generate these weights more dynamically
        #     ultralisk_weight = .8
        #     mutalisk_weight = .7
        #     hydralisk_weight = .2
        #     roach_weight = .1
        #     zergling_weight = .9
        #     if self.should_build_ultralisk() and random.random() < ultralisk_weight:
        #         bot_logger.log_action(self, "building ultralisk")
        #         await self.do(larva.train(
        #             UnitTypeId.ULTRALISK
        #         ))
        #     elif self.should_build_mutalisk() and random.random() < mutalisk_weight:
        #         bot_logger.log_action(self, "building mutalisk")
        #         await self.do(larva.train(
        #             UnitTypeId.MUTALISK))
        #     elif self.should_build_hydralisk() and random.random() < hydralisk_weight:
        #         bot_logger.log_action(self, "building hydralisk")
        #         await self.do(larva.train(UnitTypeId.HYDRALISK))
        #     elif self.should_build_roach() and random.random() < roach_weight:
        #         bot_logger.log_action(self, "building roach")
        #         await self.do(larva.train(UnitTypeId.ROACH))
        #     elif self.should_build_zergling() and random.random() < zergling_weight:
        #         await build_zergling(self, larva)
    async def build_military_units(self):
        larvae = self.units(UnitTypeId.LARVA).ready
        if larvae.exists:
            larva = larvae.random
            # TODO generate these weights more dynamically
            ultralisk_weight = .8
            mutalisk_weight = .7
            hydralisk_weight = .2
            roach_weight = .1
            zergling_weight = .9
            if self.should_build_ultralisk() and random.random() < ultralisk_weight:
                bot_logger.log_action(self, "building ultralisk")
                return await self.do(larva.train(
                    UnitTypeId.ULTRALISK
                ))
            if self.should_build_mutalisk() and random.random() < mutalisk_weight:
                bot_logger.log_action(self, "building mutalisk")
                return await self.do(larva.train(
                    UnitTypeId.MUTALISK))
            if self.should_build_hydralisk() and random.random() < hydralisk_weight:
                bot_logger.log_action(self, "building hydralisk")
                return await self.do(larva.train(UnitTypeId.HYDRALISK))
            if self.should_build_roach() and random.random() < roach_weight:
                bot_logger.log_action(self, "building roach")
                return await self.do(larva.train(UnitTypeId.ROACH))
            if self.should_build_zergling() and random.random() < zergling_weight:
                return await build_zergling(self, larva)

    def should_build_gas(self) -> bool:
        has_excess_vespene = self.vespene > 1000
        is_late_game = self.time > 2000
        if has_excess_vespene and not is_late_game:
            return False
        extractor_count = self.units(UnitTypeId.EXTRACTOR).amount
        ideal_extractor_count = 0
        if self.expansion_count != 0 and self.time > 68:
            ideal_extractor_count += 1
        if self.time > 255:
            ideal_extractor_count += 2
        if self.time > 200:
            ideal_extractor_count += 1
        if self.time > 300:
            ideal_extractor_count += 1
        if self.time > 334:
            ideal_extractor_count = math.inf
        
        
        return extractor_count < ideal_extractor_count
        # extractors = self.units(UnitTypeId.EXTRACTOR)
        # extractor_count = extractors.amount
        # if extractor_count < 1 and self.expansion_count < 1 and self.time > 60:
        #     return True
        # elif extractor_count < 2 and self.time > 120:
        #     return True
        # elif extractor_count < 3 and self.time > 300:
        #     return True
        # elif extractor_count < 4 and self.time > 500:
        #     return True
        # elif extractor_count >= 4:
        #     return True
        # else:
        #     return False

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

    def on_end(self, game_result: Result):
        bot_logger.log_action(self, game_result)
        if self.should_show_plot:
            plot_dir = get_plot_directory()
            make_dir_if_not_exists(plot_dir)
            figure_name = get_figure_name(game_result)
            self.plotter.save(figure_name)
