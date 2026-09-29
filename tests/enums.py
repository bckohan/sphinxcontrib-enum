import inspect
import typing as t
from dataclasses import dataclass, field
from enum import Enum, IntEnum, IntFlag, StrEnum
from typing import NamedTuple

from docutils import nodes
from enum_properties import EnumProperties, IntEnumProperties, Symmetric, p, s


class Plain(IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3

    @property
    def square(self) -> int:
        return self.value**2


class Perm(IntFlag):
    R = 4
    W = 2
    X = 1


class Shape(StrEnum):
    CIRCLE = "circle"
    SQUARE = "square"


# -- dataclass mixin --------------------------------------------------------------


@dataclass(frozen=True)
class PlanetData:
    mass: float
    radius: float


class Planet(PlanetData, Enum):
    MERCURY = 3.303e23, 2.4397e6
    VENUS = 4.869e24, 6.0518e6
    EARTH = 5.976e24, 6.37814e6


# -- dataclass values --------------------------------------------------------------


@dataclass(frozen=True)
class RGB:
    r: int
    g: int
    b: int


class ColorValue(Enum):
    RED = RGB(255, 0, 0)
    GREEN = RGB(0, 255, 0)


# -- namedtuple values -------------------------------------------------------------


class Point(NamedTuple):
    x: int
    y: int


class Corner(Enum):
    ORIGIN = Point(0, 0)
    FAR = Point(10, 10)


# -- enum-properties ----------------------------------------------------------------


class Color(EnumProperties):
    label: t.Annotated[str, Symmetric()]
    hex: str
    rgb: tuple[int, int, int]
    shapes: list[Shape]

    RED = 1, "Red", "ff0000", (1, 0, 0), [Shape.CIRCLE]
    GREEN = 2, "Green", "00ff00", (0, 1, 0), [Shape.CIRCLE, Shape.SQUARE]
    BLUE = 3, "Blue", "0000ff", (0, 0, 1), []


class Level(IntEnumProperties, s("label"), s("abbr"), p("rank"), p("parent")):
    LOW = 0, "Low", "L", 1.5, None
    MID = 1, "Medium, Mostly", "M", 2.5, Shape.CIRCLE
    HIGH = 2, 'High "quoted"', "H", None, {"k": Shape.SQUARE}


# -- enum-properties + dataclass ---------------------------------------------------


@dataclass
class Info:
    label: str
    weight: int


class Tagged(Info, EnumProperties):
    code: str

    ALPHA = "Alpha", 1, "a"
    BETA = "Beta", 2, "b"


class Outer:
    class Inner(Enum):
        A = "a"


class Empty(Enum):
    pass


NOT_AN_ENUM = 5


# -- formatters ----------------------------------------------------------------------


def format_hex(member, column, value):
    if column == "hex":
        return nodes.literal(f"#{value}", f"#{value}")
    if column == "label":
        return value.upper()
    return None


def format_paragraph(member, column, value):
    if column == "label":
        return nodes.paragraph("", "", nodes.strong(value, value))
    return None


# -- large table (latex longtable) ---------------------------------------------------


@dataclass(frozen=True)
class Spec:
    description: str
    code: str
    weight: float


_LONG = (
    "a fairly long description of this member that should wrap onto several "
    "lines inside the table cell rather than running off the page"
)

Wide = Enum(
    "Wide",
    {
        f"MEMBER_{idx}": (
            _LONG if idx % 3 == 0 else "short",
            f"CODE_{idx}_$%&#{{}}~^\\",
            idx * 1.5,
        )
        for idx in range(60)
    },
    type=Spec,
    module=__name__,
)


# -- member docstrings ---------------------------------------------------------------


class Documented(PlanetData, Enum):
    """The class docstring must never be used as a member docstring."""

    MERCURY = 3.303e23, 2.4397e6
    """The *smallest* planet, see ``Planet.MERCURY``."""

    #: The hottest planet.
    VENUS = 4.869e24, 6.0518e6

    EARTH = 5.976e24, 6.37814e6


@dataclass(frozen=True)
class Described:
    code: str
    doc: str


class DocOverride(Described, Enum):
    ALPHA = "a", "field doc for alpha"
    """Docstring for alpha.

    A second paragraph.
    """

    BETA = "b", "field doc for beta"


class DocField(Described, Enum):
    ALPHA = "a", "field doc for alpha"
    BETA = "b", "field doc for beta"


class ExplicitDoc(Enum):
    ONE = 1, "Explicit doc for one."
    TWO = 2, None

    def __init__(self, value, doc):
        if doc:
            self.__doc__ = doc


class Holder:
    class Nested(Enum):
        X = 1
        """Nested member doc."""


def format_doc(member, column, value):
    if column == "doc":
        return f"[{value}]"
    return None


# -- column legend -----------------------------------------------------------------


@dataclass(frozen=True)
class LegendBase:
    mass: float
    """Mass in *kilograms*."""


# python 3.14+ supports dataclasses.field(doc=...)
FIELD_DOCS = "doc" in inspect.signature(field).parameters


@dataclass(frozen=True)
class LegendData(LegendBase):
    #: Radius in meters.
    radius: float

    moons: int = field(default=0, **({"doc": "Number of moons."} if FIELD_DOCS else {}))

    rings: bool = False


class LegendPlanet(LegendData, Enum):
    EARTH = 5.976e24, 6.37814e6, 1
    """Home."""

    SATURN = 5.683e26, 5.8232e7, 146, True

    @property
    def density(self) -> float:
        """Mean density in kg/m³."""
        return self.mass / (4 / 3 * 3.14159 * self.radius**3)


class LegendColor(EnumProperties):
    label: t.Annotated[str, Symmetric()]
    """Human readable label."""

    #: Hex code, without the leading ``#``.
    hex: str

    rgb: tuple[int, int, int]

    RED = 1, "Red", "ff0000", (1, 0, 0)
    GREEN = 2, "Green", "00ff00", (0, 1, 0)


class LegendPoint(NamedTuple):
    x: int
    """Horizontal position."""

    y: int


class LegendCorner(Enum):
    ORIGIN = LegendPoint(0, 0)
