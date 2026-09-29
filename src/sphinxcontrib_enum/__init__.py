r"""
::

        ███████╗██████╗ ██╗  ██╗██╗███╗   ██╗██╗  ██╗
        ██╔════╝██╔══██╗██║  ██║██║████╗  ██║╚██╗██╔╝
        ███████╗██████╔╝███████║██║██╔██╗ ██║ ╚███╔╝
        ╚════██║██╔═══╝ ██╔══██║██║██║╚██╗██║ ██╔██╗
        ███████║██║     ██║  ██║██║██║ ╚████║██╔╝ ██╗
        ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝

     ██████╗ ██████╗ ███╗   ██╗████████╗██████╗ ██╗██████╗
    ██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔══██╗██║██╔══██╗
    ██║     ██║   ██║██╔██╗ ██║   ██║   ██████╔╝██║██████╔╝
    ██║     ██║   ██║██║╚██╗██║   ██║   ██╔══██╗██║██╔══██╗
    ╚██████╗╚██████╔╝██║ ╚████║   ██║   ██║  ██║██║██████╔╝
     ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═════╝

            ███████╗███╗   ██╗██╗   ██╗███╗   ███╗
            ██╔════╝████╗  ██║██║   ██║████╗ ████║
            █████╗  ██╔██╗ ██║██║   ██║██╔████╔██║
            ██╔══╝  ██║╚██╗██║██║   ██║██║╚██╔╝██║
            ███████╗██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
            ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝

Sphinx directive for documenting dataclass enums in tabular format, with support for
enum-properties.
"""

__title__ = "sphinxcontrib-enum"
__version__ = "0.3.0"
__author__ = "Brian Kohan"
__license__ = "MIT"
__copyright__ = "Copyright 2026 Brian Kohan"

import typing as t
from pathlib import Path

from sphinx.application import Sphinx

from . import directive
from .directive import EnumTableDirective, Formatter
from .introspect import (
    column_docstrings,
    default_columns,
    format_value,
    import_enum,
    member_docstrings,
    resolve,
)

__all__ = [
    "EnumTableDirective",
    "Formatter",
    "column_docstrings",
    "default_columns",
    "format_value",
    "import_enum",
    "member_docstrings",
    "resolve",
    "setup",
]

STATIC_DIR = Path(__file__).parent / "static"

BASE_CSS = "sphinxcontrib_enum.css"

THEME_CSS = {"furo": "sphinxcontrib_enum_furo.css"}
"""Additional stylesheets for specific html themes, keyed by ``html_theme``."""


def _add_static_files(app: Sphinx) -> None:
    # let sphinx copy (and refresh) our css with the rest of the static files, a new
    # list is assigned so we never mutate a default shared between applications
    app.config.html_static_path = [*app.config.html_static_path, str(STATIC_DIR)]
    theme_css = THEME_CSS.get(app.config.html_theme)
    if theme_css:
        # after the base stylesheet so theme rules take precedence
        app.add_css_file(theme_css, priority=501)


def setup(app: Sphinx) -> dict[str, t.Any]:
    directive.setup(app)
    app.add_css_file(BASE_CSS)
    app.connect("builder-inited", _add_static_files)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
