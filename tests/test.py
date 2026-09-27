import csv
import io
import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sphinx.application import Sphinx
from sphinx.util.console import nocolor
from sphinx.util.docutils import docutils_namespace

import sphinxcontrib_enum
from sphinxcontrib_enum.introspect import (
    default_columns,
    format_value,
    import_enum,
    resolve,
    to_json_value,
)
from tests.enums import (
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
        [td.get_text(strip=True) for td in tr.select("td")]
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
    out, warnings = build(tmp_path, ".. enum-table:: tests.enums.Color\n")
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
    out, warnings = build(tmp_path, ".. enum-table:: tests.enums.Level\n")
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
    out, warnings = build(tmp_path, ".. enum-table:: tests.enums.Planet\n")
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


def test_download_disabled_globally(tmp_path):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.Plain\n", enum_table_download=[]
    )
    assert not warnings
    assert not soup(out).select("div.enum-table-downloads")
    assert not (out / "_downloads").exists()


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
        )
        assert not warnings
        page = soup(out, page_path)
        link = page.select_one("a.enum-table-download")
        assert link["href"].startswith("../../")
        assert ((out / page_path).parent / link["href"]).resolve().is_file()


def test_singlehtml(tmp_path):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.Plain\n", builder="singlehtml"
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
        tmp_path, ".. enum-table:: tests.enums.Color\n", builder="text"
    )
    assert not warnings
    text = (out / "index.txt").read_text()
    assert "ff0000" in text
    assert "CSV" not in text and "JSON" not in text


def test_latex_builder(tmp_path):
    out, warnings = build(
        tmp_path, ".. enum-table:: tests.enums.Planet\n", builder="latex"
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
        """,
        engine,
        numfig=True,
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
