.. include:: ./refs.rst
.. role:: big

==================
sphinxcontrib-enum
==================


.. only:: html


    .. image:: https://img.shields.io/badge/License-MIT-blue.svg
        :target: https://opensource.org/licenses/MIT
        :alt: MIT License

    .. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
        :target: https://docs.astral.sh/ruff
        :alt: Ruff

    .. image:: https://badge.fury.io/py/sphinxcontrib-enum.svg
        :target: https://pypi.python.org/pypi/sphinxcontrib-enum/
        :alt: PyPI Version

    .. image:: https://img.shields.io/pypi/pyversions/sphinxcontrib-enum.svg
        :target: https://pypi.python.org/pypi/sphinxcontrib-enum/
        :alt: Python Versions

    .. image:: https://img.shields.io/pypi/status/sphinxcontrib-enum.svg
        :target: https://pypi.python.org/pypi/sphinxcontrib-enum
        :alt: Development Status

    .. image:: https://img.shields.io/pypi/types/sphinxcontrib-enum.svg
        :target: https://pypi.python.org/pypi/sphinxcontrib-enum
        :alt: Typed

    .. image:: https://readthedocs.org/projects/sphinxcontrib-enum/badge/?version=latest
        :target: http://sphinxcontrib-enum.readthedocs.io/?badge=latest/
        :alt: Documentation Status

    .. image:: https://codecov.io/gh/bckohan/sphinxcontrib-enum/branch/main/graph/badge.svg?token=0IZOKN2DYL
        :target: https://codecov.io/gh/bckohan/sphinxcontrib-enum
        :alt: Code Coverage

    .. image:: https://github.com/bckohan/sphinxcontrib-enum/actions/workflows/test.yml/badge.svg?branch=main
        :target: https://github.com/bckohan/sphinxcontrib-enum/actions/workflows/test.yml
        :alt: Test Status

    .. image:: https://github.com/bckohan/sphinxcontrib-enum/actions/workflows/lint.yml/badge.svg
        :target: https://github.com/bckohan/sphinxcontrib-enum/actions/workflows/lint.yml
        :alt: Lint Status
    .. image:: https://api.securityscorecards.dev/projects/github.com/bckohan/sphinxcontrib-enum/badge
        :target: https://securityscorecards.dev/viewer/?uri=github.com/bckohan/sphinxcontrib-enum
        :alt: OSSF Scorecard


A Sphinx_ directive for documenting dataclass_ enums in tabular format. Each member is a row and
each dataclass field is a column. Tables can optionally be downloaded as CSV or JSON.

* Documents enums that mix in a dataclass_ or whose values are dataclasses (or named tuples).
* Columns may be any attribute, property or dotted path on the member or its value.
* Filter and reorder columns and members, rename headers, add captions and cross references.
* Member docstrings are rendered in a ``doc`` column.
* Optional :ref:`column legends <column_legend>` from field and property docstrings.
* Customize how cells render with a formatter function.
* Optional CSV and JSON download buttons (html builders only).
* :ref:`Supports enum-properties <enum_properties>` enums as a special case, and plain enums work
  too.

For example:

.. tabs::

   .. tab:: Dataclass

      Each dataclass field becomes a column, and field docstrings can describe them in a
      legend:

      .. literalinclude:: ./examples.py
         :language: python
         :start-after: # [dataclass]
         :end-before: # [dataclass]

      .. code-block:: rst

         .. enum-table:: examples.Planet
            :legend:
            :download: csv, json

      .. enum-table:: examples.Planet
         :legend:

   .. tab:: Docstrings

      :ref:`Member docstrings <member_docstrings>` are rendered in a ``doc`` column:

      .. literalinclude:: ./examples.py
         :language: python
         :start-after: # [docstrings]
         :end-before: # [docstrings]

      .. code-block:: rst

         .. enum-table:: examples.Severity

      .. enum-table:: examples.Severity
         :download:

   .. tab:: enum-properties

      :ref:`enum-properties <enum_properties>` properties become columns, described by their
      annotation docstrings:

      .. literalinclude:: ./examples.py
         :language: python
         :start-after: # [enum-properties]
         :end-before: # [enum-properties]

      .. code-block:: rst

         .. enum-table:: examples.Shade
            :legend:
            :download:

      .. enum-table:: examples.Shade
         :legend:
         :download:

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   reference/index
   changelog

.. only:: html

   .. rubric:: Indices and tables

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`
