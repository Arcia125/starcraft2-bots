
import random

import sc2
from sc2.constants import AbilityId, COMMANDCENTER, BARRACKS, SCV, MARINE, BARRACKS, SUPPLYDEPOT, MORPH_SUPPLYDEPOT_LOWER, BUNKER, REFINERY
from typing import List


class MarineBot(sc2.BotAI):
    def __init__(self):
        self.built_bunker = False

    @property
    def should_build_barracks(self) -> bool:
        return self.can_afford(BARRACKS) and (self.units(BARRACKS).amount < 3 or self.minerals > 700)

    @property
    def should_build_suppy_depot(self) -> bool:
        return self.can_afford(SUPPLYDEPOT) and not self.already_pending(SUPPLYDEPOT)\
            and (self.supply_cap - self.supply_used) < 5

    def lower_supply_depots(self) -> List["UnitCommand"]:
        actions = []
        for depot in self.units(SUPPLYDEPOT).ready:
            actions.append(depot(MORPH_SUPPLYDEPOT_LOWER))
        return actions

    def select_target(self):
        target = self.known_enemy_structures
        if target.exists:
            return target.random.position

        target = self.known_enemy_units
        if target.exists:
            return target.random.position

        if min([u.position.distance_to(self.enemy_start_locations[0]) for u in self.units]) < 5:
            return self.enemy_start_locations[0].position

        return self.state.mineral_field.random.position

    async def on_Start(self):
        self.built_barracks = False
        self.built_bunker = False

    async def on_step(self, iteration):
        cc = self.units(COMMANDCENTER)
        if not cc.ready.exists:
            return
        else:
            cc = cc.first

        if iteration % 100 == 0:
            await self.distribute_workers()

        all_barracks = self.units(BARRACKS)
        should_buy_svc = self.can_afford(
            SCV) and self.workers.amount < 16 and cc.noqueue

        if should_buy_svc:
            await self.do(cc.train(SCV))

        for rax in all_barracks:
            if rax.is_ready and rax.noqueue and self.can_afford(MARINE):
                await self.do(rax.train(MARINE))
                if self.built_bunker and self.units(BUNKER).ready.exists and iteration % 50 == 0:
                    await self.do(rax(AbilityId.RALLY_BUILDING, self.units(BUNKER).random.position))

        if self.should_build_barracks:
            await self.build(BARRACKS, near=cc.position.towards(self.game_info.map_center, 10), max_distance=500, placement_step=2)

        if self.should_build_suppy_depot:
            await self.build(SUPPLYDEPOT, near=cc, max_distance=500, placement_step=2)

        target = self.select_target()

        # if self.units(BARRACKS).ready.exists and self.can_afford(BUNKER) and not self.built_bunker:
        #     await self.build(BUNKER, near=target.towards(self.game_info.map_center, 30))
        #     self.built_bunker = True

        # if self.units(BARRACKS).ready.exists and self.units(REFINERY).amount < 2:
        #     if self.can_afford(REFINERY):
        #         vgs = self.state.vespene_geyser.closer_than(20.0, cc)
        #         for vg in vgs:
        #             if self.units(REFINERY).closer_than(1.0, vg).exists:
        #                 break

        #             worker = self.select_build_worker(vg.position)
        #             if worker is None:
        #                 break

        #             await self.do(worker.build(REFINERY, vg))
        #             break

        actions = []
        actions += self.lower_supply_depots()
        if iteration % 10 == 0 and self.units(MARINE).closer_than(10, cc).amount > 5 or self.units(MARINE).closer_than(10, target).amount > 0 or self.units(MARINE).amount > 15:
            for unit in self.units.filter(lambda x: not x.is_structure):
                if unit.is_idle:
                    actions.append(unit.attack(target))
                else:
                    enemy_threats = self.known_enemy_units.filter(
                        lambda x: x.can_attack_ground).closer_than(10, unit)
                    if enemy_threats.exists:
                        closest_enemy = enemy_threats.closest_to(unit)
                        if unit.weapon_cooldown == 0:
                            actions.append(unit.attack(closest_enemy))
                        elif closest_enemy.distance_to(unit) > 3:
                            actions.append(unit.move(closest_enemy.position))
                        elif unit.health_percentage < .5:
                            self.units.first.position.towards
                            actions.append(
                                unit.move(unit.position.towards(self.start_location, 5)))
        await self.do_actions(actions)
