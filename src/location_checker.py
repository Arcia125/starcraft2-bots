from sc2.bot_ai import BotAI
from sc2.position import Point2, Point3
from sc2.unit import Unit
from typing import Union

from src.bot_actions import get_enemies_near_position
from src.types import Location


def default_location_check(bot: BotAI, location: Location) -> bool:
    return get_enemies_near_position(bot, location)


class LocationChecker(object):
    """
    Checks a location to see if a condition is ever met. Once met,
    it will continue to return True unless reset
    """

    def __init__(self, bot: BotAI, location: Location, location_checker=default_location_check):
        self.bot = bot
        self.location = location
        self.active = False
        self.location_checker = location_checker

    def _check(self) -> bool:
        return self.location_checker(self.bot, self.location)

    def check(self) -> bool:
        if not self.active:
            is_active = self._check()
            self.active = is_active
        return self.active

    def on_step(self) -> bool:
        return self.check()

    def reset(self):
        self.active = False

    def get_location(self) -> Location:
        return self.location
