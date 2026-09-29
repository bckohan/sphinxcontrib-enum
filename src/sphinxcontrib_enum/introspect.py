"""
Introspection utilities for discovering the tabular structure of an enumeration.

These functions determine which columns an enumeration exposes, how to fetch and
serialize each cell and where member docstrings come from. They do not depend on
docutils and only use Sphinx to read docstrings from source.
"""

import csv
import dataclasses
import inspect
import io
import json
import typing as t
from enum import Enum
from importlib import import_module

from sphinx.errors import PycodeError
from sphinx.pycode import ModuleAnalyzer

__all__ = [
    "NAME",
    "VALUE",
    "column_docstrings",
    "default_columns",
    "format_value",
    "import_enum",
    "is_structured",
    "member_docstrings",
    "resolve",
    "to_csv",
    "to_json",
    "to_json_value",
]

NAME = "name"
"""The pseudo-column that holds the member's name."""

VALUE = "value"
"""The pseudo-column that holds the member's value."""


def import_enum(path: str, default_module: str | None = None) -> type[Enum]:
    """
    Import an enumeration class from an import path string.

    The path may separate the module from the class qualname with a ``:``
    (``pkg.module:Outer.Enum``) or use dots throughout (``pkg.module.Outer.Enum``),
    in which case the longest importable module prefix is used. If the path cannot
    be resolved absolutely and ``default_module`` is given, the path is also tried
    relative to that module.

    :param path: The import path of the enumeration.
    :param default_module: A module to resolve the path relative to if the path
        cannot be resolved on its own (e.g. the current ``py:module``).
    :raises ImportError: If the path cannot be resolved.
    :raises TypeError: If the path resolves to something that is not an Enum class.
    """
    candidates = [path]
    if default_module and ":" not in path:
        candidates.append(f"{default_module}.{path}")

    errors: list[str] = []
    for candidate in candidates:
        try:
            obj = _import_object(candidate)
        except (ImportError, AttributeError) as err:
            errors.append(f"{candidate}: {err}")
            continue
        if not (isinstance(obj, type) and issubclass(obj, Enum)):
            raise TypeError(f"{candidate} is not an Enum class.")
        return obj
    raise ImportError(f"Unable to import enum {path!r}: " + "; ".join(errors))


def _import_object(path: str) -> t.Any:
    if ":" in path:
        module_path, _, qualname = path.partition(":")
        obj: t.Any = import_module(module_path)
        for attr in qualname.split("."):
            obj = getattr(obj, attr)
        return obj

    parts = path.split(".")
    for idx in range(len(parts) - 1, 0, -1):
        try:
            obj = import_module(".".join(parts[:idx]))
        except ImportError:
            continue
        for attr in parts[idx:]:
            obj = getattr(obj, attr)
        return obj
    raise ImportError(f"No module found in {path!r}")


def member_docstrings(enum_cls: type[Enum]) -> dict[str, str]:
    """
    Find the docstrings of an enumeration's members, keyed by member name.

    Python does not give enum members their own docstrings (``member.__doc__`` is
    the class docstring), so docstrings are found the same way autodoc finds them,
    in order of precedence:

    1. A ``__doc__`` attribute set explicitly on the member instance (e.g. by the
       enum's ``__init__``).
    2. A string literal immediately after the member's assignment, or a ``#:``
       comment before it, in the enum's source code.

    Members without a docstring are not included. Docstrings are dedented and
    stripped but otherwise returned verbatim (they are usually reStructuredText).
    """
    docs: dict[str, str] = {}
    try:
        analyzer = ModuleAnalyzer.for_module(enum_cls.__module__)
        attr_docs = analyzer.find_attr_docs()
    except PycodeError:
        attr_docs = {}
    for member in enum_cls:
        explicit = getattr(member, "__dict__", {}).get("__doc__")
        if isinstance(explicit, str) and explicit.strip():
            docs[member.name] = inspect.cleandoc(explicit)
            continue
        lines = attr_docs.get((enum_cls.__qualname__, member.name))
        if lines and "".join(lines).strip():
            docs[member.name] = inspect.cleandoc("\n".join(lines))
    return docs


def _attr_docs(cls: type) -> dict[tuple[str, str], list[str]]:
    try:
        return ModuleAnalyzer.for_module(cls.__module__).find_attr_docs()
    except PycodeError:
        return {}


def _column_doc(classes: t.Iterable[type], column: str) -> str | None:
    for cls in classes:
        if cls is object:
            continue
        field = getattr(cls, "__dataclass_fields__", {}).get(column)
        # python 3.14+ supports dataclasses.field(doc=...)
        explicit = getattr(field, "doc", None)
        if isinstance(explicit, str) and explicit.strip():
            return inspect.cleandoc(explicit)
        lines = _attr_docs(cls).get((cls.__qualname__, column))
        if lines and "".join(lines).strip():
            return inspect.cleandoc("\n".join(lines))
        attr = cls.__dict__.get(column)
        if isinstance(attr, property) and attr.__doc__ and attr.__doc__.strip():
            return inspect.cleandoc(attr.__doc__)
    return None


def column_docstrings(enum_cls: type[Enum], columns: t.Iterable[str]) -> dict[str, str]:
    """
    Find descriptions of an enumeration's columns, keyed by column name.

    Each column is looked up on the enum's classes (including any dataclass mixin
    and its bases) and then, if the member values are dataclasses or named tuples,
    on the value's classes. For each class, in order of precedence:

    1. ``dataclasses.field(doc=...)`` (Python 3.14+).
    2. A string literal immediately after the attribute, or a ``#:`` comment before
       it, in source. This covers dataclass fields, named tuple fields and
       enum-properties property annotations.
    3. The docstring of a :class:`property` defined on the class.

    The ``name`` and ``value`` pseudo-columns and dotted column paths have no
    descriptions. Columns without a description are not included.
    """
    classes: list[type] = list(enum_cls.__mro__)
    first = next(iter(enum_cls), None)
    if first is not None and is_structured(first.value):
        classes.extend(type(first.value).__mro__)
    docs = {}
    for column in columns:
        if column in (NAME, VALUE) or "." in column:
            continue
        doc = _column_doc(classes, column)
        if doc:
            docs[column] = doc
    return docs


def is_structured(value: t.Any) -> bool:
    """
    Structured values are dataclass instances and named tuples. Their fields are
    exposed as individual columns rather than as a single value column.
    """
    return _fields_of(value) is not None


def _fields_of(obj: t.Any) -> list[str] | None:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return [field.name for field in dataclasses.fields(obj)]
    if isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return list(obj._fields)  # pyright: ignore[reportAttributeAccessIssue]
    return None


def default_columns(enum_cls: type[Enum]) -> list[str]:
    """
    Determine the default columns for an enumeration, in order:

    1. ``name``
    2. dataclass fields - if the enum mixes in a dataclass or its values are
       dataclasses or named tuples.
    3. ``value`` - only when the values are not structured (dataclass or
       namedtuple), so it never appears alongside dataclass fields.
    4. enum-properties properties - a special case for
       :class:`enum_properties.EnumProperties` classes.

    Duplicate column names are dropped, keeping the first occurrence.
    """
    columns = [NAME]
    members = list(enum_cls)
    first = members[0] if members else None

    if first is None or not is_structured(first.value):
        columns.append(VALUE)

    if first is not None:
        # a dataclass mixin makes the member itself a dataclass instance
        columns.extend(_fields_of(first) or _fields_of(first.value) or [])

    columns.extend(str(prop) for prop in getattr(enum_cls, "_properties_", []) or [])

    return list(dict.fromkeys(columns))


def resolve(member: Enum, column: str) -> t.Any:
    """
    Fetch the raw value of a column for the given member.

    Columns may be dotted attribute paths (e.g. ``value.red``). The first
    attribute is looked up on the member and then, if not found, on the member's
    value.

    :raises AttributeError: If the column cannot be resolved.
    """
    first, *rest = column.split(".")
    try:
        obj = getattr(member, first)
    except AttributeError:
        obj = getattr(member.value, first)
    for attr in rest:
        obj = getattr(obj, attr)
    return obj


def format_value(value: t.Any) -> str:
    """
    The default conversion of a cell value into display text.

    * Enum members render as ``ClassName.MEMBER``
    * Lists, tuples and sets render as comma separated values
    * Dictionaries render as comma separated ``key: value`` pairs
    * Everything else is converted with :class:`str`
    """
    if isinstance(value, Enum):
        return f"{type(value).__name__}.{value.name}"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set, frozenset)) and not is_structured(value):
        items = sorted(value, key=str) if isinstance(value, (set, frozenset)) else value
        return ", ".join(format_value(item) for item in items)
    if isinstance(value, dict):
        return ", ".join(
            f"{format_value(k)}: {format_value(v)}" for k, v in value.items()
        )
    return str(value)


def to_json_value(
    value: t.Any, fallback: t.Callable[[t.Any], str] = format_value
) -> t.Any:
    """
    Convert a cell value into a JSON serializable structure. Native JSON types are
    preserved, containers and structured values are converted recursively and
    anything else (including enum members) is converted to text with ``fallback``.
    """
    if isinstance(value, Enum):
        return fallback(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    fields = _fields_of(value)
    if fields is not None:
        return {
            field: to_json_value(getattr(value, field), fallback) for field in fields
        }
    if isinstance(value, dict):
        return {str(k): to_json_value(v, fallback) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(item, fallback) for item in value]
    if isinstance(value, (set, frozenset)):
        return [to_json_value(item, fallback) for item in sorted(value, key=str)]
    return fallback(value)


def to_csv(headers: t.Sequence[str], rows: t.Iterable[t.Sequence[str]]) -> str:
    """Render a header row and rows of display text as CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue()


def to_json(
    names: t.Sequence[str],
    columns: t.Sequence[str],
    rows: t.Iterable[t.Sequence[t.Any]],
) -> str:
    """
    Render rows of JSON serializable values as an object keyed by member name. Each
    member maps to an object keyed by column. The ``name`` column is omitted from the
    member objects because it is the key.
    """
    return json.dumps(
        {
            name: {col: val for col, val in zip(columns, row) if col != NAME}
            for name, row in zip(names, rows)
        },
        indent=2,
        ensure_ascii=False,
    )
