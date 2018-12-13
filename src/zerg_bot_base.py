from abc import ABC, abstractmethod
from sc2 import BotAI
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2, Point3
from typing import Union


class ZergBotBase(ABC, BotAI):
    def __init__(self):
        super().__init__()

    @property
    @abstractmethod
    def _is_booming_time(self) -> bool:
        """override to allow the bot to determine if it should boom"""
        pass

    @property
    @abstractmethod
    def _is_rushing_time(self) -> bool:
        """override to allow the bot to determine if it should rush"""
        pass

    @property
    @abstractmethod
    def _is_mutalisk_time(self) -> bool:
        """override to allow the bot to determine if it should build / tech mutalisks"""
        pass

    @property
    @abstractmethod
    def _is_ultralisk_time(self) -> bool:
        """override to allow the bot to determine if it should build / tech ultralisks"""
        pass

    @property
    @abstractmethod
    def _is_roach_time(self) -> bool:
        """override to allow the bot to determine if it should build / tech roaches"""
        pass

    @property
    @abstractmethod
    def _is_rushing(self) -> bool:
        """override to allow the bot to determine if it is currently rushing"""
        pass

    @abstractmethod
    def get_has_been_under_attack_recently(self, is_under_attack=False) -> bool:
        """override to allow the bot to determine if it has been under attack recently"""
        pass

    @abstractmethod
    def should_build_lair(self) -> bool:
        """override to allow the bot to determine if it should build a lair"""
        pass

    @abstractmethod
    def should_build_hive(self) -> bool:
        """override to allow the bot to determine if it should build a hive"""
        pass

    @abstractmethod
    def should_build_spire(self) -> bool:
        """override to allow the bot to determine if it should build a spire"""
        pass

    @abstractmethod
    def should_build_gas(self) -> bool:
        """override to allow the bot to determine if it should build gas"""
        pass

    @abstractmethod
    def should_build_expansion(self) -> bool:
        """override to allow the bot to determine if it should build an expansion"""

    @abstractmethod
    def get_rally_point(self) -> Point2:
        """override to allow the bot to determine where to rally combat units"""
        pass

    @abstractmethod
    def get_townhalls_under_attack(self) -> Units:
        """override to allow the bot to determine which townhalls are under attack currently"""
        pass

    @abstractmethod
    async def on_game_step(self, iteration):
        """override to allow the bot to perform actions every game step"""
        pass

    async def first_iteration(self):
        """override to allow the bot to perform actions at the beginning of the game"""
        pass

    async def on_step(self, iteration):
        if iteration == 0:
            await self.first_iteration()

        await self.on_game_step(iteration)
