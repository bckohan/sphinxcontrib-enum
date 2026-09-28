"""
The ``enum-table`` directive and the download node it emits.
"""

import hashlib
import inspect
import re
import typing as t
from enum import Enum
from html import escape
from importlib import import_module
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.errors import ConfigError
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective, SphinxTranslator
from sphinx.util.osutil import ensuredir, relative_uri

from .introspect import (
    NAME,
    default_columns,
    format_value,
    import_enum,
    resolve,
    to_csv,
    to_json,
    to_json_value,
)

__all__ = [
    "DOWNLOAD_DIR",
    "DOWNLOAD_FORMATS",
    "EnumTableDirective",
    "Formatter",
    "download_formats",
    "enum_table_downloads",
]

logger = logging.getLogger(__name__)

Formatter = t.Callable[[Enum, str, t.Any], "str | nodes.Node | None"]
"""
The signature of a cell formatter. Formatters are passed the enum member, the
column name and the raw column value and return either the display text, a
docutils node or ``None`` to fall back to the default formatting.
"""

DOWNLOAD_FORMATS = ("csv", "json")
"""The supported download formats."""

DOWNLOAD_DIR = "_downloads/sphinxcontrib_enum"
"""The directory relative to the html output directory that download files go in."""

_MAX_AUTO_WIDTH = 40

_DOWNLOAD_ICON = (
    '<svg aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">'
    '<path fill="currentColor" d="M8 1a.75.75 0 0 1 .75.75v6.69l2.22-2.22a.75.75 0 '
    "1 1 1.06 1.06l-3.5 3.5a.75.75 0 0 1-1.06 0l-3.5-3.5a.75.75 0 1 1 1.06-1.06L7.25 "
    "8.44V1.75A.75.75 0 0 1 8 1ZM2.75 12.5a.75.75 0 0 0 0 1.5h10.5a.75.75 0 0 0 0-1.5"
    'H2.75Z"/></svg>'
)


class enum_table_downloads(nodes.General, nodes.Element):
    """
    A node holding the content of the table's download files. The html writer
    writes the files to the output directory and renders links to them, all other
    builders drop the node.

    Attributes:

    * ``basename``: the file name to use for the downloads, without extension
    * ``files``: a list of ``(format, content)`` tuples
    """


def _split(argument: str | None) -> list[str]:
    return [item for item in re.split(r"[\s,]+", argument or "") if item]


def columns_option(argument: str | None) -> list[str]:
    columns = _split(argument)
    if not columns:
        raise ValueError("at least one column is required.")
    return columns


def headers_option(argument: str | None) -> dict[str, str]:
    """Parse a comma separated list of ``column=Header`` pairs."""
    headers: dict[str, str] = {}
    for pair in (argument or "").split(","):
        if not pair.strip():
            continue
        column, sep, header = pair.partition("=")
        if not sep or not column.strip():
            raise ValueError(f"expected column=Header, got {pair.strip()!r}")
        headers[column.strip()] = header.strip()
    return headers


def download_formats(value: t.Any) -> list[str]:
    """
    Normalize a download setting into a list of formats.

    * falsey values (``False``, ``None``, empty) disable downloads
    * ``True`` enables every supported format
    * strings are comma or whitespace separated formats (or ``none``)
    * any other iterable is a collection of formats

    :raises ValueError: If a format is not supported.
    """
    if not value:
        return []
    if value is True:
        return list(DOWNLOAD_FORMATS)
    items = _split(value) if isinstance(value, str) else list(value)
    formats = [str(fmt).strip().lower() for fmt in items]
    if formats == ["none"]:
        return []
    for fmt in formats:
        if fmt not in DOWNLOAD_FORMATS:
            raise ValueError(
                f"unsupported download format {fmt!r}, "
                f"expected one of: {', '.join(DOWNLOAD_FORMATS)} or none"
            )
    return list(dict.fromkeys(formats))


def download_option(argument: str | None) -> list[str]:
    return download_formats(argument)


def widths_option(argument: str | None) -> str | list[int]:
    if (argument or "").strip().lower() in ("auto", "grid"):
        return (argument or "").strip().lower()
    return directives.positive_int_list(argument or "")


def _load_formatter(formatter: t.Any) -> Formatter | None:
    if formatter is None or callable(formatter):
        return t.cast("Formatter | None", formatter)
    module, _, attr = str(formatter).replace(":", ".").rpartition(".")
    return t.cast(Formatter, getattr(import_module(module), attr))


class EnumTableDirective(SphinxDirective):
    """
    Render an enumeration as a table with a row for each member and a column for
    the name, value and each property or dataclass field.

    .. code-block:: rst

        .. enum-table:: import.path.to.Enum
            :columns: name, mass, radius, moons
            :exclude: moons
            :members: EARTH, MARS
            :exclude-members: VENUS
            :headers: mass=Mass (kg), radius=Radius (m)
            :caption: The planets.
            :name: planet-table
            :class: my-class
            :widths: auto
            :download: csv, json
            :formatter: import.path.to.formatter
    """

    required_arguments = 1
    optional_arguments = 0
    has_content = False

    option_spec: t.ClassVar[dict[str, t.Callable[[str], t.Any]]] = {
        "columns": columns_option,
        "exclude": _split,
        "members": _split,
        "exclude-members": _split,
        "headers": headers_option,
        "caption": directives.unchanged_required,
        "name": directives.unchanged,
        "class": directives.class_option,
        "widths": widths_option,
        "download": download_option,
        "formatter": directives.unchanged_required,
    }

    def run(self) -> list[nodes.Node]:
        try:
            enum_cls = import_enum(
                self.arguments[0], self.env.ref_context.get("py:module")
            )
        except (ImportError, TypeError) as err:
            return self._warn(str(err))

        try:
            self.env.note_dependency(inspect.getfile(enum_cls))
        except (TypeError, OSError):  # pragma: no cover - builtin/dynamic enums
            pass

        try:
            formatter = _load_formatter(
                self.options.get("formatter", self.config.enum_table_formatter)
            )
        except (ImportError, AttributeError, ValueError) as err:
            return self._warn(f"Unable to import formatter: {err}")

        members = self._members(enum_cls)
        columns = self._columns(enum_cls, members)
        if not columns:
            return self._warn(f"No columns to render for {enum_cls.__qualname__}.")

        headers = self._headers(columns)
        display: list[list[str | nodes.Node]] = []
        raw: list[list[t.Any]] = []
        for member in members:
            display.append([])
            raw.append([])
            for column in columns:
                value = resolve(member, column)
                cell = formatter(member, column, value) if formatter else None
                if cell is None:
                    cell = format_value(value)
                display[-1].append(cell)
                raw[-1].append(value)

        table = self._table(headers, columns, display)
        messages: list[nodes.Node] = []
        if "caption" in self.options:
            inline, parse_messages = self.parse_inline(
                self.options["caption"], lineno=self.lineno
            )
            messages.extend(parse_messages)
            table.insert(0, nodes.title(self.options["caption"], "", *inline))
        self.set_source_info(table)
        self.add_name(table)

        container = nodes.container(classes=["enum-table-container"])
        container += table

        formats = self.options.get(
            "download", download_formats(self.config.enum_table_download)
        )
        if formats:
            text = [[_text(cell) for cell in row] for row in display]
            contents = {
                "csv": lambda: to_csv(headers, text),
                "json": lambda: to_json(
                    [member.name for member in members],
                    columns,
                    [
                        [_json(value, txt) for value, txt in zip(raw_row, text_row)]
                        for raw_row, text_row in zip(raw, text)
                    ],
                ),
            }
            container += enum_table_downloads(
                basename=enum_cls.__qualname__,
                files=[(fmt, contents[fmt]()) for fmt in formats],
            )

        return [container, *messages]

    def _warn(self, message: str) -> list[nodes.Node]:
        logger.warning(
            message, location=self.get_location(), type="enum_table", subtype="error"
        )
        return []

    def _members(self, enum_cls: type[Enum]) -> list[Enum]:
        members = list(enum_cls)
        if "members" in self.options:
            by_name = {member.name: member for member in members}
            selected = []
            for name in self.options["members"]:
                if name in by_name:
                    selected.append(by_name[name])
                else:
                    self._warn(f"{enum_cls.__qualname__} has no member {name!r}.")
            members = selected
        exclude = set(self.options.get("exclude-members", []))
        return [member for member in members if member.name not in exclude]

    def _columns(self, enum_cls: type[Enum], members: list[Enum]) -> list[str]:
        columns = self.options.get("columns", None) or default_columns(enum_cls)
        exclude = set(self.options.get("exclude", []))
        resolved = []
        for column in columns:
            if column in exclude:
                continue
            try:
                for member in members:
                    resolve(member, column)
            except AttributeError:
                self._warn(
                    f"Unable to resolve column {column!r} for "
                    f"{enum_cls.__qualname__}.{member.name}."
                )
                continue
            resolved.append(column)
        return resolved

    def _headers(self, columns: list[str]) -> list[str]:
        headers = self.options.get("headers", {})
        for column in headers:
            if column not in columns:
                self._warn(f"Header given for unknown column {column!r}.")
        return [headers.get(column, column) for column in columns]

    def _table(
        self,
        headers: list[str],
        columns: list[str],
        rows: list[list[str | nodes.Node]],
    ) -> nodes.table:
        widths = self.options.get("widths", "auto")
        table = nodes.table(classes=["enum-table", *self.options.get("class", [])])
        if widths == "auto":
            table["classes"].append("colwidths-auto")
        elif isinstance(widths, list):
            if len(widths) != len(columns):
                self._warn(
                    f"{len(widths)} widths given for {len(columns)} columns, "
                    "using equal widths."
                )
                widths = "grid"
            else:
                table["classes"].append("colwidths-given")

        if widths == "auto":
            # content based hints for writers that need widths (e.g. text)
            table["enum_auto_widths"] = True
            widths = [
                min(
                    max(len(_text(cell)) for cell in [header, *(r[idx] for r in rows)]),
                    _MAX_AUTO_WIDTH,
                )
                for idx, header in enumerate(headers)
            ]
        elif not isinstance(widths, list):
            widths = [100 // len(columns)] * len(columns)

        tgroup = nodes.tgroup(cols=len(columns))
        table += tgroup
        for width in widths:
            tgroup += nodes.colspec(colwidth=max(width, 1))

        thead = nodes.thead()
        tgroup += thead
        thead += self._row([nodes.paragraph(header, header) for header in headers])

        # enum data should be rendered verbatim
        tbody = nodes.tbody(support_smartquotes=False)
        tgroup += tbody
        for row in rows:
            tbody += self._row(
                [
                    _cell(cell, literal=column == NAME)
                    for cell, column in zip(row, columns)
                ]
            )
        return table

    @staticmethod
    def _row(cells: list[nodes.Node]) -> nodes.row:
        row = nodes.row()
        for cell in cells:
            entry = nodes.entry()
            entry += cell
            row += entry
        return row


def _text(cell: "str | nodes.Node") -> str:
    return cell if isinstance(cell, str) else cell.astext()


def _json(value: t.Any, text: str) -> t.Any:
    """
    Convert a raw cell value to JSON. Top level values that are not natively
    serializable use the cell's display text (respecting any custom formatter).
    """
    return to_json_value(
        value, lambda item: text if item is value else format_value(item)
    )


def _cell(cell: "str | nodes.Node", literal: bool = False) -> nodes.Node:
    if isinstance(cell, str):
        cell = nodes.literal(cell, cell) if literal else nodes.Text(cell)
    elif isinstance(cell, nodes.Body):
        return cell
    return nodes.paragraph("", "", cell)


# -- Writers ----------------------------------------------------------------------


def visit_downloads_html(self: SphinxTranslator, node: enum_table_downloads) -> None:
    builder = self.builder
    base_uri = builder.get_target_uri(
        getattr(builder, "current_docname", None) or builder.config.root_doc
    )
    links = []
    for fmt, content in node["files"]:
        filename = f"{node['basename']}.{fmt}"
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        target = f"{DOWNLOAD_DIR}/{digest}/{filename}"
        path = Path(builder.outdir) / target
        ensuredir(path.parent)
        path.write_text(content, encoding="utf-8")
        links.append(
            f'<a class="enum-table-download reference download" '
            f'href="{escape(relative_uri(base_uri, target))}" '
            f'download="{escape(filename)}" '
            f'title="Download {escape(node["basename"])} as {fmt.upper()}">'
            f"{_DOWNLOAD_ICON}<span>{fmt.upper()}</span></a>"
        )
    self.body.append(  # type: ignore[attr-defined]
        f'<div class="enum-table-downloads">{"".join(links)}</div>'
    )
    raise nodes.SkipNode


def _remove_downloads(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    """Downloads are only supported by the html builders (excluding epub)."""
    if app.builder.format != "html" or app.builder.name.startswith("epub"):
        for node in list(doctree.findall(enum_table_downloads)):
            node.parent.remove(node)


# sphinx's latex writer switches to longtable when a table has more than this many rows
_LATEX_LONGTABLE_ROWS = 30

# width hint adjustments, in characters, for typeset latex columns
_LATEX_LITERAL_SCALE = 1.3
_LATEX_CELL_PADDING = 3


def _wrap_latex_longtables(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    """
    Sphinx renders longtables with non-wrapping ``l`` columns unless column widths
    are given, and only Sphinx 9+ caps their cells so long text wraps. For latex
    builds, give large enum tables proportional widths from the content based hints
    so their cells wrap on every supported Sphinx version.
    """
    if app.builder.format != "latex":
        return
    for table in doctree.findall(nodes.table):
        classes = table["classes"]
        if "enum-table" not in classes or "colwidths-given" in classes:
            continue
        rows = list(table.findall(nodes.row))
        if len(rows) > _LATEX_LONGTABLE_ROWS or "longtable" in classes:
            classes.append("colwidths-given")
            if table.get("enum_auto_widths"):
                _latex_width_hints(table, rows)


def _latex_width_hints(table: nodes.table, rows: list[nodes.row]) -> None:
    """
    Adjust the character count width hints for typesetting: every column pays for
    its cell padding and literal (monospace) columns need more room per character.
    """
    body = [row for row in rows if isinstance(row.parent, nodes.tbody)]
    for idx, colspec in enumerate(table.findall(nodes.colspec)):
        cells = [row[idx] for row in body if idx < len(row)]
        literal = bool(cells) and all(
            next(iter(cell.findall(nodes.literal)), None) is not None for cell in cells
        )
        width = colspec["colwidth"] * (_LATEX_LITERAL_SCALE if literal else 1)
        colspec["colwidth"] = round(width) + _LATEX_CELL_PADDING


def _check_download_config(app: Sphinx, config: Config) -> None:
    try:
        download_formats(config.enum_table_download)
    except (TypeError, ValueError) as err:
        raise ConfigError(f"Invalid enum_table_download: {err}") from err


def setup(app: Sphinx) -> None:
    app.add_node(
        enum_table_downloads,
        html=(visit_downloads_html, None),
    )
    app.add_directive("enum-table", EnumTableDirective)
    app.connect("doctree-resolved", _remove_downloads)
    app.connect("doctree-resolved", _wrap_latex_longtables)
    app.add_config_value(
        "enum_table_download",
        False,
        "env",
        # frozenset/set must not be listed, sphinx converts sequences to frozensets
        # when they are, losing the format order
        types=(bool, list, tuple, str, type(None)),
    )
    app.connect("config-inited", _check_download_config)
    app.add_config_value("enum_table_formatter", None, "env")
