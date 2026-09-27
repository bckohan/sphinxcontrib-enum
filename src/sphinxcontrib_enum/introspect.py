"""
Introspection utilities for discovering the tabular structure of an enumeration.

These functions have no dependency on Sphinx or docutils and determine which columns
an enumeration exposes and how to fetch and serialize each cell.
"""

import csv
import dataclasses
import io
import json
import typing as t
from enum import Enum
from importlib import import_module

__all__ = [
    "NAME",
    "VALUE",
    "default_columns",
    "format_value",
    "import_enum",
    "is_structured",
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
