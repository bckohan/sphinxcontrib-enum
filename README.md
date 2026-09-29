# sphinxcontrib-enum
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI version](https://badge.fury.io/py/sphinxcontrib-enum.svg)](https://pypi.python.org/pypi/sphinxcontrib-enum/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/sphinxcontrib-enum.svg)](https://pypi.python.org/pypi/sphinxcontrib-enum/)
[![PyPI status](https://img.shields.io/pypi/status/sphinxcontrib-enum.svg)](https://pypi.python.org/pypi/sphinxcontrib-enum)
[![Documentation Status](https://readthedocs.org/projects/sphinxcontrib-enum/badge/?version=latest)](http://sphinxcontrib-enum.readthedocs.io/?badge=latest/)
[![Code Cov](https://codecov.io/gh/bckohan/sphinxcontrib-enum/branch/main/graph/badge.svg?token=0IZOKN2DYL)](https://codecov.io/gh/bckohan/sphinxcontrib-enum)
[![Test Status](https://github.com/bckohan/sphinxcontrib-enum/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/bckohan/sphinxcontrib-enum/actions/workflows/test.yml?query=branch:main)
[![Lint Status](https://github.com/bckohan/sphinxcontrib-enum/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/bckohan/sphinxcontrib-enum/actions/workflows/lint.yml?query=branch:main)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/bckohan/sphinxcontrib-enum/badge)](https://securityscorecards.dev/viewer/?uri=github.com/bckohan/sphinxcontrib-enum)

Sphinx directive for documenting dataclass enums in tabular format, with support for enum-properties.

Render [dataclass](https://docs.python.org/3/library/dataclasses.html) enums as tables with a row for each member and a column for every field. Tables can optionally offer CSV and JSON download buttons. Enums with dataclass values, named tuple values and plain enums work too, and [enum-properties](https://enum-properties.readthedocs.io) enums are also supported!

## Installation

```bash
pip install sphinxcontrib-enum
```

To document [enum-properties](https://enum-properties.readthedocs.io) enums, install the `properties` extra to get a supported version of enum-properties:

```bash
pip install "sphinxcontrib-enum[properties]"
```

Add the extension to your `conf.py`:

```python
extensions = [
    ...
    "sphinxcontrib_enum",
]
```

## Quick Start

### Dataclass Enums

Each dataclass field becomes a column. Field docstrings can describe the columns in an optional legend:

```python
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class PlanetData:
    mass: float
    """Mass in kilograms."""

    radius: float
    """Radius in meters."""

    #: Number of known moons.
    moons: int


class Planet(PlanetData, Enum):
    MERCURY = 3.303e23, 2.4397e6, 0
    VENUS = 4.869e24, 6.0518e6, 0
    EARTH = 5.976e24, 6.37814e6, 1
    MARS = 6.421e23, 3.3972e6, 2
```

```rst
.. enum-table:: mypackage.Planet
   :legend:
   :download:
```

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bckohan/sphinxcontrib-enum/main/doc/images/dataclass-dark.png">
  <img alt="The Planet enum rendered as a table with name, mass, radius and moons columns, a legend describing each column and CSV and JSON download buttons" src="https://raw.githubusercontent.com/bckohan/sphinxcontrib-enum/main/doc/images/dataclass-light.png" width="380">
</picture>

### Member Docstrings

Member docstrings are rendered in a `doc` column. They are parsed as reStructuredText:

```python
from enum import IntEnum


class Severity(IntEnum):
    DEBUG = 10
    """Diagnostic detail, usually disabled in production."""

    INFO = 20
    """Routine operational messages."""

    #: Something unexpected happened that the application **recovered** from.
    WARNING = 30

    ERROR = 40
    """A failure that needs attention.

    See :ref:`usage` for how to render these tables."""

    CRITICAL = 50
```

```rst
.. enum-table:: mypackage.Severity
   :download:
```

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bckohan/sphinxcontrib-enum/main/doc/images/docstrings-dark.png">
  <img alt="The Severity enum rendered as a table with name, value and doc columns, the doc column holding each member's rendered docstring" src="https://raw.githubusercontent.com/bckohan/sphinxcontrib-enum/main/doc/images/docstrings-light.png" width="713">
</picture>

### enum-properties

[enum-properties](https://enum-properties.readthedocs.io) properties become columns, described by their annotation docstrings:

```python
import typing as t

from enum_properties import EnumProperties, Symmetric


class Shade(EnumProperties):
    label: t.Annotated[str, Symmetric()]
    """A human readable label."""

    hex: t.Annotated[str, Symmetric(case_fold=True)]
    """The hex color code, without a leading ``#``."""

    RED = 1, "Red", "ff0000"
    GREEN = 2, "Green", "00ff00"
    BLUE = 3, "Blue", "0000ff"
```

```rst
.. enum-table:: mypackage.Shade
   :legend:
   :download:
```

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bckohan/sphinxcontrib-enum/main/doc/images/enum-properties-dark.png">
  <img alt="The Shade enum rendered as a table with name, value, label and hex columns and a legend describing the label and hex columns" src="https://raw.githubusercontent.com/bckohan/sphinxcontrib-enum/main/doc/images/enum-properties-light.png" width="287">
</picture>

Columns, members, headers, widths, captions, download formats and cell formatting can all be customized:

```rst
.. enum-table:: mypackage.Planet
   :columns: name, radius
   :members: EARTH, MERCURY
   :headers: name=Planet, radius=Radius (m)
   :caption: The inner planets.
```

## Documentation

Full documentation is available at [sphinxcontrib-enum.readthedocs.io](https://sphinxcontrib-enum.readthedocs.io).

## Development

```bash
git clone https://github.com/bckohan/sphinxcontrib-enum.git
cd sphinxcontrib-enum
just setup
just install
just test
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).
