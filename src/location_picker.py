from sc2.bot_ai import BotAI
from sc2.unit import Unit
from sc2.position import Point2, Point3
from typing import Union, Dict

from src.location_checker import LocationChecker, default_location_check
from src.types import Location


class LocationPicker(object):
    def __init__(self, bot: BotAI, location_options: Dict[str, Location] = {}, location_checker=default_location_check):
        self.bot = bot
        self.location_checkers = {}
        for checker_key, location in location_options.items():
            self.add_location_checker(checker_key, location)

    def add_location_checker(self, checker_key, location):
        self.location_checkers[checker_key] = LocationChecker(
            self.bot, location)

    def check(self) -> Dict[str, LocationChecker]:
        active_checkers = {}
        for checker_key, checker in self.location_checkers.items():
            if checker.active or checker.check():
                active_checkers[checker_key] = checker
        return active_checkers

    def get_inactive(self) -> Dict[str, LocationChecker]:
        inactive_checkers = {}
        for checker_key, checker in self.location_checkers.items():
            if not checker.active or not checker.check():
                inactive_checkers[checker_key] = checker
        return inactive_checkers

    def on_step(self) -> Dict[str, LocationChecker]:
        active_checkers = {}
        for checker_key, checker in self.location_checkers.items():
            if checker.active or checker.on_step():
                active_checkers[checker_key] = checker
        return active_checkers
