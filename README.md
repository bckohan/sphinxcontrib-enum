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

Render [dataclass](https://docs.python.org/3/library/dataclasses.html) enums as tables with a row for each member and a column for every field. Each table has CSV and JSON download buttons. Enums with dataclass values, named tuple values and plain enums work too, and [enum-properties](https://enum-properties.readthedocs.io) enums are supported as a special case: each property becomes a column.

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

Given a dataclass enum:

```python
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class PlanetData:
    mass: float
    radius: float


class Planet(PlanetData, Enum):
    MERCURY = 3.303e23, 2.4397e6
    VENUS = 4.869e24, 6.0518e6
    EARTH = 5.976e24, 6.37814e6
```

Document it with:

```rst
.. enum-table:: mypackage.Planet
   :caption: The inner planets.
```

Which renders a table with `name`, `mass` and `radius` columns. Columns, members, headers, widths, download formats and cell formatting can all be customized:

```rst
.. enum-table:: mypackage.Planet
   :columns: name, radius
   :members: EARTH, MERCURY
   :headers: name=Planet, radius=Radius (m)
   :download: csv
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
