"""Example enumerations rendered in the documentation."""

import typing as t
from dataclasses import dataclass
from enum import Enum, IntEnum

from docutils import nodes
from enum_properties import EnumProperties, Symmetric


# [dataclass]
@dataclass(frozen=True)
class PlanetData:
    mass: float
    """Mass in kilograms."""

    radius: float
    """Radius in meters."""

    moons: int


class Planet(PlanetData, Enum):
    MERCURY = 3.303e23, 2.4397e6, 0
    VENUS = 4.869e24, 6.0518e6, 0
    EARTH = 5.976e24, 6.37814e6, 1
    MARS = 6.421e23, 3.3972e6, 2
# [dataclass]


# [dataclass-value]
@dataclass(frozen=True)
class RGB:
    red: int
    green: int
    blue: int


class Color(Enum):
    RED = RGB(255, 0, 0)
    GREEN = RGB(0, 255, 0)
    BLUE = RGB(0, 0, 255)
# [dataclass-value]


# [plain]
class Priority(IntEnum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10

    @property
    def urgent(self) -> bool:
        return self >= Priority.HIGH
# [plain]


# [enum-properties]
class Shade(EnumProperties):
    label: t.Annotated[str, Symmetric()]
    hex: t.Annotated[str, Symmetric(case_fold=True)]

    RED = 1, "Red", "ff0000"
    GREEN = 2, "Green", "00ff00"
    BLUE = 3, "Blue", "0000ff"
# [enum-properties]


# [formatter]
def planet_formatter(member: Enum, column: str, value: t.Any):
    if column in ("mass", "radius"):
        unit = "kg" if column == "mass" else "m"
        return nodes.Text(f"{value:.3e} {unit}")
    return None  # use the default formatting
# [formatter]
