import csv
import io
import json
import os
import shutil
import subprocess
import sys
import textwrap
from enum import Enum
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sphinx.application import Sphinx
from sphinx.errors import ConfigError
from sphinx.util.console import nocolor
from sphinx.util.docutils import docutils_namespace

import sphinxcontrib_enum
from sphinxcontrib_enum.introspect import (
    default_columns,
    format_value,
    column_docstrings,
    import_enum,
    member_docstrings,
    resolve,
    to_json_value,
)
from tests.enums import (
    LegendColor,
    LegendCorner,
    LegendPlanet,
    DocField,
    DocOverride,
    Documented,
    ExplicitDoc,
    Holder,
    RGB,
    Color,
    ColorValue,
    Corner,
    Empty,
    Level,
    Outer,
    Perm,
    Plain,
    Planet,
    Point,
    Shape,
    Tagged,
)

# -- helpers ------------------------------------------------------------------------


def build(tmp_path: Path, rst: str, builder: str = "html", **conf) -> tuple[Path, str]:
    """
    Build a single page sphinx project containing the given rst and return the output
    directory and the warnings emitted during the build.
    """
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    (src / "conf.py").write_text(
        "extensions = ['sphinxcontrib_enum']\n"
        + "".join(f"{key} = {value!r}\n" for key, value in conf.items())
    )
    (src / "index.rst").write_text("Test\n====\n\n" + textwrap.dedent(rst))
    out = tmp_path / "out" / builder
    warnings = io.StringIO()
    nocolor()
    with docutils_namespace():
        app = Sphinx(
            srcdir=src,
            confdir=src,
            outdir=out,
            doctreedir=tmp_path / "doctrees" / builder,
            buildername=builder,
            status=None,
            warning=warnings,
            freshenv=True,
        )
        app.build()
    return out, warnings.getvalue()


def soup(out: Path, page: str = "index.html") -> BeautifulSoup:
    return BeautifulSoup((out / page).read_text(), "html.parser")


def table_data(page: BeautifulSoup, idx: int = 0) -> tuple[list[str], list[list[str]]]:
    table = page.select("table.enum-table")[idx]
    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    rows = [
        [" ".join(td.get_text().split()) for td in tr.select("td")]
        for tr in table.select("tbody tr")
    ]
    return headers, rows


def downloads(out: Path, page: BeautifulSoup, idx: int = 0) -> dict[str, str]:
    container = page.select("div.enum-table-downloads")[idx]
    files = {}
    for link in container.select("a.enum-table-download"):
        path = (out / link["href"]).resolve()
        assert path.is_file()
        files[link["download"]] = path.read_text()
    return files


# -- introspection --------------------------------------------------------------------


def test_metadata():
    assert sphinxcontrib_enum.__title__ == "sphinxcontrib-enum"


@pytest.mark.parametrize(
    "enum_cls, expected",
    [
        (Plain, ["name", "value"]),
        (Perm, ["name", "value"]),
        (Shape, ["name", "value"]),
        (Planet, ["name", "mass", "radius"]),
        (ColorValue, ["name", "r", "g", "b"]),
        (Corner, ["name", "x", "y"]),
        (Color, ["name", "value", "label", "hex", "rgb", "shapes"]),
        (Level, ["name", "value", "label", "abbr", "rank", "parent"]),
        (Tagged, ["name", "label", "weight", "code"]),
        (Empty, ["name", "value"]),
    ],
)
def test_default_columns(enum_cls, expected):
    assert default_columns(enum_cls) == expected


def test_resolve():
    assert resolve(Planet.EARTH, "mass") == 5.976e24
    assert resolve(ColorValue.RED, "r") == 255
    assert resolve(ColorValue.RED, "value.g") == 0
    assert resolve(ColorValue.RED, "value") == RGB(255, 0, 0)
    assert resolve(Corner.FAR, "y") == 10
    assert resolve(Color.GREEN, "hex") == "00ff00"
    assert resolve(Plain.THREE, "square") == 9
    assert resolve(Plain.THREE, "name") == "THREE"
    with pytest.raises(AttributeError):
        resolve(Plain.ONE, "missing")
    with pytest.raises(AttributeError):
        resolve(ColorValue.RED, "value.missing")


def test_format_value():
    assert format_value(None) == "None"
    assert format_value(1.5) == "1.5"
    assert format_value("text") == "text"
    assert format_value(Shape.CIRCLE) == "Shape.CIRCLE"
    assert format_value((1, 0, 0)) == "1, 0, 0"
    assert format_value([Shape.CIRCLE, Shape.SQUARE]) == "Shape.CIRCLE, Shape.SQUARE"
    assert format_value({"b", "a"}) == "a, b"
    assert format_value({"k": Shape.SQUARE}) == "k: Shape.SQUARE"
    assert format_value(Point(1, 2)) == "Point(x=1, y=2)"
    assert format_value(RGB(1, 2, 3)) == "RGB(r=1, g=2, b=3)"


def test_to_json_value():
    assert to_json_value(None) is None
    assert to_json_value(True) is True
    assert to_json_value(Shape.CIRCLE) == "Shape.CIRCLE"
    assert to_json_value((1, [Shape.SQUARE])) == [1, ["Shape.SQUARE"]]
    assert to_json_value(frozenset({2, 1})) == [1, 2]
    assert to_json_value({1: RGB(1, 2, 3)}) == {"1": {"r": 1, "g": 2, "b": 3}}
    assert to_json_value(Point(1, 2)) == {"x": 1, "y": 2}
    assert to_json_value(object, fallback=lambda v: "obj") == "obj"


def test_import_enum():
    assert import_enum("tests.enums.Color") is Color
    assert import_enum("tests.enums:Color") is Color
    assert import_enum("tests.enums.Outer.Inner") is Outer.Inner
    assert import_enum("tests.enums:Outer.Inner") is Outer.Inner
    assert import_enum("Outer.Inner", "tests.enums") is Outer.Inner
    assert import_enum("enum.Enum") is not None
    with pytest.raises(ImportError):
        import_enum("tests.enums.Missing")
    with pytest.raises(ImportError):
        import_enum("tests.enums:Missing")
    with pytest.raises(ImportError):
        import_enum("nomodule")
    with pytest.raises(TypeError):
        import_enum("tests.enums.NOT_AN_ENUM")
    with pytest.raises(TypeError):
        import_enum("tests.enums.RGB")


# -- directive: html -------------------------------------------------------------------


def test_enum_properties_table(tmp_path):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.Color\n", enum_table_download=True
    )
    assert not warnings
    page = soup(out)
    headers, rows = table_data(page)
    assert headers == ["name", "value", "label", "hex", "rgb", "shapes"]
    assert rows == [
        ["RED", "1", "Red", "ff0000", "1, 0, 0", "Shape.CIRCLE"],
        ["GREEN", "2", "Green", "00ff00", "0, 1, 0", "Shape.CIRCLE, Shape.SQUARE"],
        ["BLUE", "3", "Blue", "0000ff", "0, 0, 1", ""],
    ]
    # names are rendered as literals
    assert page.select_one("table.enum-table tbody td code").get_text() == "RED"
    # auto widths - no explicit column widths
    assert not page.select("table.enum-table col[style]")
    assert (out / "_static" / "sphinxcontrib_enum.css").is_file()
    assert page.find("link", href=lambda h: h and "sphinxcontrib_enum.css" in h)

    files = downloads(out, page)
    assert set(files) == {"Color.csv", "Color.json"}
    assert list(csv.reader(io.StringIO(files["Color.csv"]))) == [headers, *rows]
    data = json.loads(files["Color.json"])
    # keyed on member name, in definition order
    assert list(data) == ["RED", "GREEN", "BLUE"]
    assert data == {
        "RED": {
            "value": 1,
            "label": "Red",
            "hex": "ff0000",
            "rgb": [1, 0, 0],
            "shapes": ["Shape.CIRCLE"],
        },
        "GREEN": {
            "value": 2,
            "label": "Green",
            "hex": "00ff00",
            "rgb": [0, 1, 0],
            "shapes": ["Shape.CIRCLE", "Shape.SQUARE"],
        },
        "BLUE": {
            "value": 3,
            "label": "Blue",
            "hex": "0000ff",
            "rgb": [0, 0, 1],
            "shapes": [],
        },
    }


def test_csv_escaping(tmp_path):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.Level\n", enum_table_download=True
    )
    assert not warnings
    page = soup(out)
    headers, rows = table_data(page)
    assert rows[1] == ["MID", "1", "Medium, Mostly", "M", "2.5", "Shape.CIRCLE"]
    files = downloads(out, page)
    assert list(csv.reader(io.StringIO(files["Level.csv"]))) == [headers, *rows]
    data = json.loads(files["Level.json"])
    assert data["LOW"]["parent"] is None
    assert data["HIGH"]["label"] == 'High "quoted"'
    assert data["HIGH"]["rank"] is None
    assert data["HIGH"]["parent"] == {"k": "Shape.SQUARE"}


def test_dataclass_mixin_table(tmp_path):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.Planet\n", enum_table_download=True
    )
    assert not warnings
    page = soup(out)
    headers, rows = table_data(page)
    assert headers == ["name", "mass", "radius"]
    assert rows[2] == ["EARTH", "5.976e+24", "6378140.0"]
    assert json.loads(downloads(out, page)["Planet.json"])["EARTH"] == {
        "mass": 5.976e24,
        "radius": 6378140.0,
    }


def test_dataclass_value_table(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.ColorValue

        .. enum-table:: tests.enums.ColorValue
            :columns: name value
        """,
        enum_table_download=True,
    )
    assert not warnings
    page = soup(out)
    assert table_data(page, 0) == (
        ["name", "r", "g", "b"],
        [["RED", "255", "0", "0"], ["GREEN", "0", "255", "0"]],
    )
    assert table_data(page, 1)[1][0] == ["RED", "RGB(r=255, g=0, b=0)"]
    assert json.loads(downloads(out, page, 1)["ColorValue.json"])["RED"] == {
        "value": {"r": 255, "g": 0, "b": 0},
    }


def test_namedtuple_and_tagged_tables(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Corner

        .. enum-table:: tests.enums.Tagged
        """,
    )
    assert not warnings
    page = soup(out)
    assert table_data(page, 0) == (
        ["name", "x", "y"],
        [["ORIGIN", "0", "0"], ["FAR", "10", "10"]],
    )
    assert table_data(page, 1) == (
        ["name", "label", "weight", "code"],
        [["ALPHA", "Alpha", "1", "a"], ["BETA", "Beta", "2", "b"]],
    )


def test_options(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Color
            :columns: label, hex, value, name, rgb
            :exclude: rgb
            :members: BLUE GREEN RED
            :exclude-members: GREEN
            :headers: hex=Hex Code, label = Label,
            :caption: The *colors*.
            :name: color-table
            :class: custom another
            :widths: 1 2 1 1

        See :numref:`color-table` and :ref:`color-table`.
        """,
        numfig=True,
        enum_table_download=True,
    )
    assert not warnings
    page = soup(out)
    headers, rows = table_data(page)
    assert headers == ["Label", "Hex Code", "value", "name"]
    assert rows == [["Blue", "0000ff", "3", "BLUE"], ["Red", "ff0000", "1", "RED"]]
    table = page.select_one("table.enum-table")
    assert {"custom", "another"} <= set(table["class"])
    assert table["id"] == "color-table"
    assert table.caption.select_one(".caption-number").get_text(strip=True) == "Table 1"
    assert table.caption.select_one(".caption-text").get_text() == "The colors."
    assert table.caption.select_one("em").get_text() == "colors"
    assert [
        float(col["style"].removeprefix("width:").strip(" %"))
        for col in table.select("col")
    ] == [20, 40, 20, 20]
    assert page.select_one('a[href="#color-table"]')
    files = downloads(out, page)
    assert list(csv.reader(io.StringIO(files["Color.csv"]))) == [headers, *rows]
    # keyed on member name in the rendered member order
    assert json.loads(files["Color.json"]) == {
        "BLUE": {"label": "Blue", "hex": "0000ff", "value": 3},
        "RED": {"label": "Red", "hex": "ff0000", "value": 1},
    }


def test_json_keyed_without_name_column(tmp_path):
    """The member name is the json key even when it is not a rendered column."""
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Color
            :columns: hex
        """,
        enum_table_download=True,
    )
    assert not warnings
    page = soup(out)
    assert table_data(page) == (["hex"], [["ff0000"], ["00ff00"], ["0000ff"]])
    assert json.loads(downloads(out, page)["Color.json"]) == {
        "RED": {"hex": "ff0000"},
        "GREEN": {"hex": "00ff00"},
        "BLUE": {"hex": "0000ff"},
    }


def test_computed_property_column(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Plain
            :columns: name value square
            :widths: grid
        """,
    )
    assert not warnings
    page = soup(out)
    assert table_data(page)[1] == [
        ["ONE", "1", "1"],
        ["TWO", "2", "4"],
        ["THREE", "3", "9"],
    ]
    # grid widths are only rendered in html when table_style has colwidths-grid
    assert not page.select("table.enum-table col[style]")


def test_download_option(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Plain
            :download: none

        .. enum-table:: tests.enums.Plain
            :download: JSON

        .. enum-table:: tests.enums.Plain
        """,
        enum_table_download=["csv"],
    )
    assert not warnings
    page = soup(out)
    containers = page.select("div.enum-table-container")
    assert len(containers) == 3
    assert not containers[0].select("div.enum-table-downloads")
    assert set(downloads(out, page, 0)) == {"Plain.json"}
    assert set(downloads(out, page, 1)) == {"Plain.csv"}


@pytest.mark.parametrize(
    "conf",
    [
        {},  # disabled by default
        {"enum_table_download": False},
        {"enum_table_download": None},
        {"enum_table_download": []},
        {"enum_table_download": ()},
        {"enum_table_download": ""},
        {"enum_table_download": "none"},
    ],
)
def test_download_disabled_globally(tmp_path, conf):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Plain

        .. enum-table:: tests.enums.Plain
            :download: json
        """,
        **conf,
    )
    assert not warnings
    page = soup(out)
    containers = page.select("div.enum-table-container")
    assert not containers[0].select("div.enum-table-downloads")
    # tables can still opt in when downloads are disabled globally
    assert set(downloads(out, page)) == {"Plain.json"}


@pytest.mark.parametrize(
    "setting, expected",
    [
        (True, ["Plain.csv", "Plain.json"]),
        (["json"], ["Plain.json"]),
        (("JSON", "csv"), ["Plain.json", "Plain.csv"]),
        ("json, csv", ["Plain.json", "Plain.csv"]),
        (["json", "csv"], ["Plain.json", "Plain.csv"]),
    ],
)
def test_download_config_values(tmp_path, setting, expected):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.Plain\n", enum_table_download=setting
    )
    assert not warnings
    links = soup(out).select("a.enum-table-download")
    assert [link["download"] for link in links] == expected


@pytest.mark.parametrize("setting", [["xml"], "csv yaml", ["none", "csv"]])
def test_download_config_invalid(tmp_path, setting):
    with pytest.raises(ConfigError, match="Invalid enum_table_download"):
        build(
            tmp_path, ".. enum-table:: tests.enums.Plain\n", enum_table_download=setting
        )


def test_download_links_relative(tmp_path):
    src = tmp_path / "src" / "sub" / "deeper"
    src.mkdir(parents=True)
    (src / "page.rst").write_text("Page\n====\n\n.. enum-table:: tests.enums.Plain\n")
    for builder, page_path in (
        ("html", "sub/deeper/page.html"),
        ("dirhtml", "sub/deeper/page/index.html"),
    ):
        out, warnings = build(
            tmp_path,
            ".. toctree::\n\n   sub/deeper/page\n",
            builder=builder,
            enum_table_download=True,
        )
        assert not warnings
        page = soup(out, page_path)
        link = page.select_one("a.enum-table-download")
        assert link["href"].startswith("../../")
        assert ((out / page_path).parent / link["href"]).resolve().is_file()


def test_singlehtml(tmp_path):
    out, warnings = build(
        tmp_path,
        ".. enum-table:: tests.enums.Plain\n",
        builder="singlehtml",
        enum_table_download=True,
    )
    assert not warnings
    page = soup(out)
    assert set(downloads(out, page)) == {"Plain.csv", "Plain.json"}


def test_currentmodule(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. currentmodule:: tests.enums

        .. enum-table:: Outer.Inner
        """,
    )
    assert not warnings
    assert table_data(soup(out)) == (["name", "value"], [["A", "a"]])


def test_formatters(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Color
            :columns: name label hex

        .. enum-table:: tests.enums.Color
            :columns: name label
            :formatter: tests.enums:format_paragraph
        """,
        enum_table_formatter="tests.enums.format_hex",
        enum_table_download=True,
    )
    assert not warnings
    page = soup(out)
    assert table_data(page, 0)[1][0] == ["RED", "RED", "#ff0000"]
    first = page.select("table.enum-table")[0]
    assert first.select("tbody tr")[0].select("td")[2].code.get_text() == "#ff0000"
    assert table_data(page, 1)[1][0] == ["RED", "Red"]
    second = page.select("table.enum-table")[1]
    assert second.select("tbody tr")[0].select("td")[1].strong.get_text() == "Red"

    files = downloads(out, page, 0)
    assert list(csv.reader(io.StringIO(files["Color.csv"])))[1] == [
        "RED",
        "RED",
        "#ff0000",
    ]
    # json keeps native values
    assert json.loads(files["Color.json"])["RED"] == {
        "label": "Red",
        "hex": "ff0000",
    }


def test_formatter_json_fallback(tmp_path):
    """Non-native top level values use the formatted display text in json."""
    (tmp_path / "fmt").mkdir()
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Level
            :columns: name parent
            :formatter: tests.test:format_parent
        """,
        enum_table_download=True,
    )
    assert not warnings
    page = soup(out)
    data = json.loads(downloads(out, page)["Level.json"])
    assert data["MID"]["parent"] == "circle!"
    assert data["HIGH"]["parent"] == {"k": "Shape.SQUARE"}


def format_parent(member, column, value):
    if isinstance(value, Shape):
        return f"{value.value}!"
    return None


# -- member docstrings ---------------------------------------------------------------


def test_member_docstrings():
    assert member_docstrings(Documented) == {
        "MERCURY": "The *smallest* planet, see ``Planet.MERCURY``.",
        "VENUS": "The hottest planet.",
    }
    assert member_docstrings(DocOverride) == {
        "ALPHA": "Docstring for alpha.\n\nA second paragraph."
    }
    assert member_docstrings(ExplicitDoc) == {"ONE": "Explicit doc for one."}
    assert member_docstrings(Holder.Nested) == {"X": "Nested member doc."}
    # no member docstrings - the class docstring is never used
    assert member_docstrings(DocField) == {}
    assert member_docstrings(Planet) == {}
    assert member_docstrings(Plain) == {}
    # enums without source have no member docstrings
    assert member_docstrings(Enum("Functional", "A B")) == {}
    assert member_docstrings(Enum("NoSource", "A B", module="no_such_module")) == {}


def test_doc_column(tmp_path):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.Documented\n", enum_table_download=True
    )
    assert not warnings
    page = soup(out)
    headers, rows = table_data(page)
    assert headers == ["name", "mass", "radius", "doc"]
    assert [row[-1] for row in rows] == [
        "The smallest planet, see Planet.MERCURY.",
        "The hottest planet.",
        "",
    ]
    # docstrings are parsed as restructured text
    cell = page.select("table.enum-table tbody tr")[0].select("td")[-1]
    assert cell.em.get_text() == "smallest"
    assert cell.code.get_text() == "Planet.MERCURY"
    # downloads get the rendered text
    files = downloads(out, page)
    csv_rows = list(csv.reader(io.StringIO(files["Documented.csv"])))
    assert csv_rows[0] == headers
    assert [row[-1] for row in csv_rows[1:]] == [row[-1] for row in rows]
    data = json.loads(files["Documented.json"])
    assert data["MERCURY"]["doc"] == "The smallest planet, see Planet.MERCURY."
    assert data["EARTH"]["doc"] == ""


def test_doc_column_overrides_existing(tmp_path):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.DocOverride\n", enum_table_download=True
    )
    assert not warnings
    page = soup(out)
    headers, rows = table_data(page)
    # the docstring column replaces the doc field in place
    assert headers == ["name", "code", "doc"]
    assert rows == [
        ["ALPHA", "a", "Docstring for alpha. A second paragraph."],
        ["BETA", "b", ""],
    ]
    cell = page.select("table.enum-table tbody tr")[0].select("td")[-1]
    assert [p.get_text() for p in cell.select("p")] == [
        "Docstring for alpha.",
        "A second paragraph.",
    ]
    data = json.loads(downloads(out, page)["DocOverride.json"])
    assert data["ALPHA"]["doc"] == "Docstring for alpha.\n\nA second paragraph."


def test_doc_column_without_docstrings(tmp_path):
    """Without member docstrings a doc column is an ordinary column."""
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.DocField

        .. enum-table:: tests.enums.Planet
        """,
    )
    assert not warnings
    page = soup(out)
    assert table_data(page, 0) == (
        ["name", "code", "doc"],
        [["ALPHA", "a", "field doc for alpha"], ["BETA", "b", "field doc for beta"]],
    )
    assert table_data(page, 1)[0] == ["name", "mass", "radius"]


def test_docs_option(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Documented
            :docs: false

        .. enum-table:: tests.enums.DocOverride
            :docs: no

        .. enum-table:: tests.enums.Documented
            :docs:

        .. enum-table:: tests.enums.Documented
            :docs: On
        """,
    )
    assert not warnings
    page = soup(out)
    assert table_data(page, 0)[0] == ["name", "mass", "radius"]
    # with docs off an existing doc column shows its own values
    assert table_data(page, 1)[1][0] == ["ALPHA", "a", "field doc for alpha"]
    assert table_data(page, 2)[0][-1] == "doc"
    assert table_data(page, 3)[0][-1] == "doc"


def test_doc_column_option(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.DocOverride
            :doc-column: description
            :headers: description=Description
        """,
        enum_table_download=True,
    )
    assert not warnings
    page = soup(out)
    headers, rows = table_data(page)
    # renamed doc column does not override the doc field
    assert headers == ["name", "code", "doc", "Description"]
    assert rows[0][2:] == [
        "field doc for alpha",
        "Docstring for alpha. A second paragraph.",
    ]
    data = json.loads(downloads(out, page)["DocOverride.json"])
    assert data["ALPHA"]["description"] == "Docstring for alpha.\n\nA second paragraph."
    assert data["ALPHA"]["doc"] == "field doc for alpha"


def test_doc_column_explicit_columns(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Documented
            :columns: doc name

        .. enum-table:: tests.enums.Documented
            :columns: name mass

        .. enum-table:: tests.enums.Documented
            :exclude: doc

        .. enum-table:: tests.enums.Documented
            :members: EARTH

        .. enum-table:: tests.enums.Documented
            :exclude-members: MERCURY

        .. enum-table:: tests.enums.Documented
            :columns: name doc
            :docs: false
        """,
    )
    page = soup(out)
    assert table_data(page, 0) == (
        ["doc", "name"],
        [
            ["The smallest planet, see Planet.MERCURY.", "MERCURY"],
            ["The hottest planet.", "VENUS"],
            ["", "EARTH"],
        ],
    )
    # explicit columns do not get the doc column appended
    assert table_data(page, 1)[0] == ["name", "mass"]
    assert table_data(page, 2)[0] == ["name", "mass", "radius"]
    # only rendered members count
    assert table_data(page, 3)[0] == ["name", "mass", "radius"]
    assert table_data(page, 4) == (
        ["name", "mass", "radius", "doc"],
        [
            ["VENUS", "4.869e+24", "6051800.0", "The hottest planet."],
            ["EARTH", "5.976e+24", "6378140.0", ""],
        ],
    )
    # docs off - doc is an ordinary (unresolvable) column
    assert table_data(page, 5)[0] == ["name"]
    assert "Unable to resolve column 'doc'" in warnings


def test_doc_column_sources(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.ExplicitDoc
            :exclude: value

        .. enum-table:: tests.enums.Holder.Nested
        """,
    )
    assert not warnings
    page = soup(out)
    assert table_data(page, 0) == (
        ["name", "doc"],
        [["ONE", "Explicit doc for one."], ["TWO", ""]],
    )
    assert table_data(page, 1) == (
        ["name", "value", "doc"],
        [["X", "1", "Nested member doc."]],
    )


def test_doc_column_formatter(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.Documented
            :columns: name doc
            :formatter: tests.enums.format_doc
        """,
    )
    assert not warnings
    # formatters receive the raw docstring
    assert [row[1] for row in table_data(soup(out))[1]] == [
        "[The *smallest* planet, see ``Planet.MERCURY``.]",
        "[The hottest planet.]",
        "[]",
    ]


# -- column legend -------------------------------------------------------------------


def legend(page: BeautifulSoup, idx: int = 0) -> list[tuple[str, str]] | None:
    container = page.select("div.enum-table-container")[idx]
    dl = container.select_one("dl.enum-table-legend")
    if dl is None:
        return None
    return [
        (dt.get_text(), " ".join(dd.get_text().split()))
        for dt, dd in zip(dl.select("dt"), dl.select("dd"))
    ]


def test_column_docstrings():
    moons = {"moons": "Number of moons."} if sys.version_info >= (3, 13) else {}
    assert column_docstrings(
        LegendPlanet,
        ["name", "value", "mass", "radius", "moons", "rings", "density", "doc"],
    ) == {
        # inherited field
        "mass": "Mass in *kilograms*.",
        # comment docs
        "radius": "Radius in meters.",
        # dataclasses.field(doc=...)
        **moons,
        # property docstrings
        "density": "Mean density in kg/m³.",
    }
    assert column_docstrings(LegendColor, ["name", "value", "label", "hex", "rgb"]) == {
        "label": "Human readable label.",
        "hex": "Hex code, without the leading ``#``.",
    }
    assert column_docstrings(LegendCorner, ["name", "x", "y"]) == {
        "x": "Horizontal position."
    }
    # properties declared as bases have no docstrings
    assert column_docstrings(Level, ["label", "abbr", "rank"]) == {}
    # dotted paths, name and value are never documented
    assert column_docstrings(LegendCorner, ["value.x", "name", "value"]) == {}
    assert column_docstrings(Empty, ["name", "value"]) == {}


def test_legend(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.LegendPlanet
            :columns: name mass radius moons rings density doc
            :headers: mass=Mass
            :legend:
        """,
    )
    assert not warnings
    page = soup(out)
    moons = [("moons", "Number of moons.")] if sys.version_info >= (3, 13) else []
    # documented columns in column order, labeled with their headers
    assert legend(page) == [
        ("Mass", "Mass in kilograms."),
        ("radius", "Radius in meters."),
        *moons,
        ("density", "Mean density in kg/m³."),
    ]
    dl = page.select_one("dl.enum-table-legend")
    # descriptions are parsed as restructured text
    assert dl.select_one("dd em").get_text() == "kilograms"
    # the table is described by its legend
    table = page.select_one("table.enum-table")
    assert table["aria-describedby"] == dl["id"]
    assert table.get("id")
    # the legend follows the table, before any downloads
    container = page.select_one("div.enum-table-container")
    assert [child.name for child in container.find_all(recursive=False)][:2] == [
        "table",
        "dl",
    ]


def test_legend_enum_properties_and_namedtuple(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.LegendColor
            :legend: true
            :name: colors

        .. enum-table:: tests.enums.LegendCorner
            :legend: yes
        """,
        enum_table_download=True,
    )
    assert not warnings
    page = soup(out)
    assert legend(page, 0) == [
        ("label", "Human readable label."),
        ("hex", "Hex code, without the leading #."),
    ]
    assert page.select_one("dl.enum-table-legend code").get_text() == "#"
    # named tables keep their id
    table = page.select("table.enum-table")[0]
    assert table["id"] == "colors"
    assert table["aria-describedby"] == page.select("dl.enum-table-legend")[0]["id"]
    assert legend(page, 1) == [("x", "Horizontal position.")]
    # legends are not included in downloads
    assert set(downloads(out, page)) == {"LegendColor.csv", "LegendColor.json"}
    # ids are unique on the page
    ids = [tag["id"] for tag in page.select("[id]")]
    assert len(ids) == len(set(ids))


def test_legend_off(tmp_path):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.LegendColor

        .. enum-table:: tests.enums.LegendColor
            :legend: false

        .. enum-table:: tests.enums.Level
            :legend:

        .. enum-table:: tests.enums.LegendColor
            :legend:
            :columns: name rgb
        """,
    )
    assert not warnings
    page = soup(out)
    # off by default, can be turned off, and omitted without documented columns
    for idx in range(4):
        assert legend(page, idx) is None
    assert not page.select("table[aria-describedby]")


def test_legend_html_visitor_fallbacks():
    """
    The aria link is skipped (and the legend still rendered) when the table start tag
    cannot be found, e.g. with a theme writer that renders tables differently.
    """
    from docutils import nodes

    from sphinxcontrib_enum.directive import enum_table_legend, visit_legend_html

    class Writer:
        def __init__(self, body):
            self.body = body
            self.visited = False

        def visit_definition_list(self, node):
            self.visited = True

    def container(first):
        legend = enum_table_legend(ids=["legend"])
        return nodes.container("", first, legend), legend

    # the table's start tag is not in the output
    _, legend = container(nodes.table(ids=["table"]))
    writer = Writer(['<div class="wrapper">', '<table class="other" id="elsewhere">'])
    visit_legend_html(writer, legend)
    assert writer.visited
    assert all("aria-describedby" not in chunk for chunk in writer.body)

    # the legend does not follow a table
    _, legend = container(nodes.paragraph())
    writer = Writer(['<table id="table">'])
    visit_legend_html(writer, legend)
    assert writer.visited
    assert writer.body == ['<table id="table">']


@pytest.mark.parametrize("builder, filename", [("text", "index.txt"), ("latex", None)])
def test_legend_other_builders(tmp_path, builder, filename):
    out, warnings = build(
        tmp_path,
        """
        .. enum-table:: tests.enums.LegendColor
            :legend:
        """,
        builder=builder,
    )
    assert not warnings
    path = out / filename if filename else next(out.glob("*.tex"))
    text = path.read_text()
    assert "Human readable label." in text
    assert "aria-describedby" not in text


# -- directive: warnings -----------------------------------------------------------------


@pytest.mark.parametrize(
    "rst, conf, message",
    [
        (".. enum-table:: tests.enums.Missing\n", {}, "Unable to import enum"),
        (".. enum-table:: tests.enums.RGB\n", {}, "is not an Enum class"),
        (
            ".. enum-table:: tests.enums.Color\n    :columns: name missing\n",
            {},
            "Unable to resolve column 'missing' for Color.RED",
        ),
        (
            ".. enum-table:: tests.enums.Color\n    :members: RED PURPLE\n",
            {},
            "Color has no member 'PURPLE'",
        ),
        (
            ".. enum-table:: tests.enums.Color\n    :headers: missing=Missing\n",
            {},
            "Header given for unknown column 'missing'",
        ),
        (
            ".. enum-table:: tests.enums.Color\n    :widths: 1 2\n",
            {},
            "2 widths given for 6 columns",
        ),
        (
            ".. enum-table:: tests.enums.Color\n    :formatter: tests.enums.nope\n",
            {},
            "Unable to import formatter",
        ),
        (
            ".. enum-table:: tests.enums.Color\n",
            {"enum_table_formatter": "nomodule.fmt"},
            "Unable to import formatter",
        ),
        (
            ".. enum-table:: tests.enums.Color\n    :columns: name\n    :exclude: name\n",
            {},
            "No columns to render for Color",
        ),
    ],
)
def test_warnings(tmp_path, rst, conf, message):
    _, warnings = build(tmp_path, rst, **conf)
    assert message in warnings
    assert "index.rst" in warnings


@pytest.mark.parametrize(
    "option",
    [
        ":docs: maybe",
        ":legend: sometimes",
        ":doc-column:",
        ":download: xml",
        ":headers: nope",
        ":headers: =Header",
        ":columns: ,",
        ":widths: fancy",
    ],
)
def test_bad_options(tmp_path, option):
    _, warnings = build(tmp_path, f".. enum-table:: tests.enums.Color\n    {option}\n")
    assert 'Error in "enum-table" directive' in warnings


def test_empty_enum(tmp_path):
    out, warnings = build(tmp_path, ".. enum-table:: tests.enums.Empty\n")
    assert not warnings
    headers, rows = table_data(soup(out))
    assert headers == ["name", "value"]
    assert rows == []


# -- other builders -----------------------------------------------------------------------


def test_text_builder(tmp_path):
    out, warnings = build(
        tmp_path,
        ".. enum-table:: tests.enums.Color\n",
        builder="text",
        enum_table_download=True,
    )
    assert not warnings
    text = (out / "index.txt").read_text()
    assert "ff0000" in text
    assert "CSV" not in text and "JSON" not in text


def test_latex_builder(tmp_path):
    out, warnings = build(
        tmp_path,
        ".. enum-table:: tests.enums.Planet\n",
        builder="latex",
        enum_table_download=True,
    )
    assert not warnings
    tex = next(out.glob("*.tex")).read_text()
    assert "MERCURY" in tex
    assert "enum-table-download" not in tex


def test_latex_longtable_widths(tmp_path):
    """Large enum tables get proportional wrapping columns in latex only."""
    rst = """
    .. enum-table:: tests.enums.Planet

    .. enum-table:: tests.enums.Planet
        :class: longtable

    .. enum-table:: tests.enums.Wide

    .. enum-table:: tests.enums.Wide
        :widths: 1 4 2 1

    .. enum-table:: tests.enums.Wide
        :widths: grid
    """
    out, warnings = build(tmp_path, rst, builder="latex")
    assert not warnings
    tex = next(out.glob("*.tex")).read_text()
    # small tables still use tabulary
    assert "\\begin{tabulary}" in tex
    longtables = tex.split("\\begin{longtable}")[1:]
    assert len(longtables) == 4
    specs = [table.split("\n", 1)[0] for table in longtables]
    assert all("\\X{" in spec and "l" not in spec.replace("\\X", "") for spec in specs)
    # given widths are respected
    assert specs[2].startswith("{\\X{1}{8}\\X{4}{8}\\X{2}{8}\\X{1}{8}")
    # grid widths stay equal
    assert specs[3].startswith("{\\X{25}{100}\\X{25}{100}\\X{25}{100}\\X{25}{100}")
    # html is untouched
    out, warnings = build(tmp_path, rst)
    assert not warnings
    assert len(soup(out).select("table.enum-table")[2].select("col[style]")) == 0


def test_epub_builder(tmp_path):
    out, warnings = build(
        tmp_path,
        ".. enum-table:: tests.enums.Plain\n",
        builder="epub",
        epub_copyright="test",
        enum_table_download=True,
    )
    assert "enum-table-download" not in (out / "index.xhtml").read_text()
    assert not (out / "_downloads").exists()


def test_rebuild_refreshes_static(tmp_path):
    """Rebuilding into the same output directory must not warn about static files."""
    out, warnings = build(tmp_path, ".. enum-table:: tests.enums.Plain\n")
    assert not warnings
    css = out / "_static" / "sphinxcontrib_enum.css"
    css.write_text("stale")
    out, warnings = build(tmp_path, ".. enum-table:: tests.enums.Plain\n")
    assert not warnings
    assert css.read_text() != "stale"


# -- pdf ------------------------------------------------------------------------------------

PDF_ENGINES = ["pdflatex", "xelatex"]


def latex_available(engine: str) -> bool:
    tools = ["make", "latexmk", engine]
    if engine == "xelatex":
        tools.append("xindy")  # sphinx's xelatex latexmkrc indexes with xindy
    return all(shutil.which(tool) for tool in tools)


def require_latex(engine: str) -> None:
    """
    Skip when the latex toolchain is not installed. CI sets REQUIRE_LATEX so a missing
    toolchain fails instead of silently skipping.
    """
    if not latex_available(engine):
        if os.getenv("REQUIRE_LATEX"):
            pytest.fail(f"REQUIRE_LATEX is set but the {engine} toolchain is missing.")
        pytest.skip(f"{engine} toolchain is not installed.")


def build_pdf(tmp_path: Path, rst: str, engine: str, **conf) -> tuple[Path, str, str]:
    """Build the rst to latex and compile it, return the pdf, warnings and latex log."""
    out, warnings = build(tmp_path, rst, builder="latex", latex_engine=engine, **conf)
    result = subprocess.run(
        ["make", "all-pdf"],
        cwd=out,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "LATEXOPTS": "-interaction=nonstopmode -halt-on-error",
        },
    )
    pdfs = list(out.glob("*.pdf"))
    assert result.returncode == 0 and pdfs, (
        result.stdout[-3000:] + result.stderr[-3000:]
    )
    log = next(out.glob("*.log")).read_text(errors="replace")
    return pdfs[0], warnings, log


def pdf_text(pdf: Path) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(pdf).pages)


def squash(text: str) -> str:
    """Remove whitespace so text wrapped across lines in table cells still matches."""
    return "".join(text.split())


@pytest.mark.parametrize("engine", PDF_ENGINES)
def test_pdf_build(tmp_path, engine):
    require_latex(engine)
    pdf, warnings, log = build_pdf(
        tmp_path,
        """
        .. enum-table:: tests.enums.Planet
            :caption: The planets.
            :name: planets

        See :numref:`planets`.

        .. enum-table:: tests.enums.Color

        .. enum-table:: tests.enums.Level
            :headers: label=Label & Name

        .. enum-table:: tests.enums.ColorValue
            :columns: name value
            :widths: 1 3

        .. enum-table:: tests.enums.Documented

        .. enum-table:: tests.enums.DocOverride

        .. enum-table:: tests.enums.LegendPlanet
            :legend:
        """,
        engine,
        numfig=True,
        enum_table_download=True,
    )
    assert not warnings
    assert "Missing character" not in log
    text = pdf_text(pdf)
    flat = squash(text)
    # captions and cross references
    assert "Table 1: The planets." in text
    assert "See Table 1" in text
    # dataclass mixin columns and values
    for expected in ("MERCURY", "VENUS", "EARTH", "5.976e+24", "6378140.0"):
        assert expected in flat
    # enum-properties columns, sequences and enum members
    assert squash("Shape.CIRCLE, Shape.SQUARE") in flat
    assert "ff0000" in flat
    # special characters, quotes and custom headers
    assert squash('High "quoted"') in flat
    assert squash("Medium, Mostly") in flat
    assert squash("Label & Name") in flat
    assert squash("RGB(r=255, g=0, b=0)") in flat
    # parsed member docstrings, including multiple paragraphs in one cell
    assert squash("The smallest planet, see Planet.MERCURY.") in flat
    assert squash("The hottest planet.") in flat
    assert squash("Docstring for alpha.") in flat
    assert squash("A second paragraph.") in flat
    # column legends
    assert squash("Mass in kilograms.") in flat
    assert squash("Radius in meters.") in flat
    # download buttons are html only
    assert "CSV" not in text and "JSON" not in text


@pytest.mark.parametrize("engine", PDF_ENGINES)
def test_pdf_longtable(tmp_path, engine):
    """
    Tables with more than 30 rows become longtables that must wrap long cells and
    break across pages.
    """
    require_latex(engine)
    pdf, warnings, log = build_pdf(
        tmp_path, ".. enum-table:: tests.enums.Wide\n", engine
    )
    assert not warnings
    tex = next(pdf.parent.glob("*.tex")).read_text()
    assert "\\begin{longtable}" in tex
    reader = PdfReader(pdf)
    table_pages = [
        idx for idx, page in enumerate(reader.pages) if "MEMBER_" in page.extract_text()
    ]
    assert len(table_pages) > 1  # the table breaks across pages
    flat = squash(pdf_text(pdf))
    for idx in range(60):
        assert f"MEMBER_{idx}" in flat
    # latex special characters are escaped
    assert squash("CODE_1_$%&#{}~^\\") in flat
    # long cells wrap instead of overflowing the page
    assert "Overfull \\hbox" not in log
