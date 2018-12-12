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
    def is_booming_time(self) -> bool:
        """override to allow the bot to determine if it should boom"""
        pass

    @property
    @abstractmethod
    def is_rushing_time(self) -> bool:
        """override to allow the bot to determine if it should rush"""
        pass

    @property
    @abstractmethod
    def is_rushing(self) -> bool:
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
    async def micro_army(self, iteration=None, is_under_attack=False, townhalls_under_attack=[]):
        """override to allow the bot to control it's army"""
        pass

    @abstractmethod
    def get_townhalls_under_attack(self) -> Units:
        """override to allow the bot to determine which townhalls are under attack currently"""
        pass
