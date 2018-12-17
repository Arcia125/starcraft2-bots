from typing import Union, List, Callable
from sc2.position import Point2, Point3
from sc2.unit import Unit

Location = Union[Unit, Point2, Point3]

UnitPredicate = Callable[[Unit], bool]
