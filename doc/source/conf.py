import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import sphinxcontrib_enum

project = sphinxcontrib_enum.__title__
copyright = sphinxcontrib_enum.__copyright__
author = sphinxcontrib_enum.__author__
release = sphinxcontrib_enum.__version__

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx_tabs.tabs",
    "sphinx.ext.viewcode",
    "sphinxcontrib_enum",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/bckohan/sphinxcontrib-enum/",
    "source_branch": "main",
    "source_directory": "doc/source",
}

html_static_path = ["_static"]
html_css_files = ["style.css"]

todo_include_todos = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
    "enum-properties": ("https://enum-properties.readthedocs.io/en/stable", None),
}

linkcheck_allow_redirects = True

# xelatex handles the unicode in the module docstring banner
latex_engine = "xelatex"

# show the download buttons on every example table
enum_table_download = True

# keep a tab open when its label is clicked again
sphinx_tabs_disable_tab_closing = True
