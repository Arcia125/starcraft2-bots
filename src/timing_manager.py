from collections import namedtuple
from typing import List, Dict
import math

from src.helpers import between


class Timing(object):
    def __init__(self, time_start=-1, time_end=math.inf):
        self.time_start = time_start
        self.time_end = time_end

    def matches(self, time):
        return between(time, self.time_start, self.time_end)

    def __repr__(self):
        return f'Timing({self.time_start}, {self.time_end})'


class TimingManager(object):
    def __init__(self, timings: Dict[str, List[Timing]] = {}):
        self.timings = timings
        self.matched_timings = set()

    def manage_timings(self, now: int):
        self.matched_timings.clear()
        for timing_name, timings in self.timings.items():
            # timing_matches = timings.matches(now)
            timing_matches = any(timing.matches(now) for timing in timings)
            if timing_matches:
                self.matched_timings.add(timing_name)

    def check_timing(self, now: int, timing_name: str) -> bool:
        timing = self.timings[timing_name]
        timing_matches = timing.matches(now)
        return timing_matches

    def is_timing(self, timing_name: str):
        return timing_name in self.matched_timings
