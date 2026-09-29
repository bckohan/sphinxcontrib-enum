.. include:: ./refs.rst

.. _usage:

=====
Usage
=====

The :rst:dir:`enum-table` directive takes the import path of an enumeration and renders a table
with a row for each member. It is designed for dataclass_ enums, where each field of the dataclass
becomes a column. By default the columns are:

1. ``name`` - the member's name.
2. dataclass fields - if the enum mixes in a dataclass_ or its values are dataclasses or named
   tuples.
3. ``value`` - the member's value, only included when the values are not dataclasses or named
   tuples.
4. enum-properties_ properties - :ref:`a special case <enum_properties>`, in the order they are
   declared.
5. ``doc`` - :ref:`member docstrings <member_docstrings>`, if any member has one.

Dataclass Enums
===============

Mixing a dataclass_ into an enumeration makes each member a dataclass instance. Each field is
rendered as a column:

.. literalinclude:: ./examples.py
   :language: python
   :start-after: # [dataclass]
   :end-before: # [dataclass]

.. code-block:: rst

   .. enum-table:: examples.Planet
      :caption: The inner planets.

.. enum-table:: examples.Planet
   :caption: The inner planets.

Dataclass Values
----------------

Enumerations whose values are dataclass (or :func:`~collections.namedtuple`) instances are rendered
the same way. The value's fields replace the ``value`` column:

.. literalinclude:: ./examples.py
   :language: python
   :start-after: # [dataclass-value]
   :end-before: # [dataclass-value]

.. code-block:: rst

   .. enum-table:: examples.Color

.. enum-table:: examples.Color

.. _member_docstrings:

Member Docstrings
=================

If any member in the table has a docstring, the docstrings are added in a column called ``doc``.
Docstrings are found the same way :mod:`~sphinx.ext.autodoc` finds them: a string literal
immediately after the member, or a ``#:`` comment before it. A ``__doc__`` attribute set on the
member itself (for example by the enum's ``__init__``) takes precedence. Members without a
docstring have an empty cell.

.. literalinclude:: ./examples.py
   :language: python
   :start-after: # [docstrings]
   :end-before: # [docstrings]

.. code-block:: rst

   .. enum-table:: examples.Severity

.. enum-table:: examples.Severity

Docstrings are parsed as reStructuredText, so inline markup, cross references and multiple
paragraphs work. CSV and JSON downloads contain the rendered text of the docstring.

* The doc column is appended after the other columns. If a column with the same name already
  exists (e.g. a dataclass field called ``doc``) the docstrings override it in place.
* Use :rst:dir:`enum-table:doc-column` to give the column a different name, for example if you
  want to keep a ``doc`` field as well as the docstrings.
* Use :rst:dir:`enum-table:docs` to turn the doc column off. The column name is then an ordinary
  column again.
* When :rst:dir:`enum-table:columns` is given, the doc column is only included where it is
  listed.
* Only the rendered members are considered. If none of them has a docstring there is no doc
  column.

.. code-block:: rst

   .. enum-table:: examples.Severity
      :doc-column: description
      :headers: description=Description

   .. enum-table:: examples.Severity
      :docs: false

.. _column_legend:

Column Legend
=============

Set :rst:dir:`enum-table:legend` to describe the table's columns in a legend beneath it. Column
descriptions come from the docstrings of the attributes behind each column:

* dataclass fields - a string literal immediately after the field, a ``#:`` comment before it, or
  ``dataclasses.field(doc=...)`` on Python 3.13+. Fields inherited from base dataclasses are
  included.
* enum-properties_ properties - docstrings on the property annotations
  (see :ref:`enum_properties`).
* named tuple fields, and properties defined with ``@property`` (their ``__doc__``).

Only documented columns are listed, in column order and labeled with their headers. If no rendered
column is documented, there is no legend. Descriptions are parsed as reStructuredText.

.. code-block:: rst

   .. enum-table:: examples.Planet
      :legend:

.. enum-table:: examples.Planet
   :legend:

The legend is a definition list, so it renders in every builder, including PDF. In HTML the table
is linked to its legend with ``aria-describedby`` so screen readers announce the descriptions
with the table. Legends are off by default.

.. note::

   Column descriptions are rendered as a visible legend rather than as tooltips on the headers
   because tooltips (``title`` attributes) are only available to mouse users and are not reliably
   announced by screen readers.

Selecting Columns
=================

Use :rst:dir:`enum-table:columns` to choose which columns are shown and in what order. Columns may
be any attribute on the member (including properties and methods decorated with ``@property``) or
a dotted path. Attributes that are not found on the member are looked up on the member's value.
Use :rst:dir:`enum-table:exclude` to drop columns from the defaults instead.

.. literalinclude:: ./examples.py
   :language: python
   :start-after: # [plain]
   :end-before: # [plain]

.. code-block:: rst

   .. enum-table:: examples.Priority
      :columns: name, value, urgent
      :headers: name=Priority, value=Weight, urgent=Urgent?

.. enum-table:: examples.Priority
   :columns: name, value, urgent
   :headers: name=Priority, value=Weight, urgent=Urgent?

Selecting Members
=================

Use :rst:dir:`enum-table:members` to choose which members are shown and in what order and
:rst:dir:`enum-table:exclude-members` to drop members.

.. code-block:: rst

   .. enum-table:: examples.Planet
      :members: EARTH, MARS
      :exclude: moons

.. enum-table:: examples.Planet
   :members: EARTH, MARS
   :exclude: moons

Formatting Cells
================

By default cells are converted to text with :func:`~sphinxcontrib_enum.format_value`. Enum members
render as ``ClassName.MEMBER``, sequences render as comma separated values and ``name`` cells
render as inline literals. You can change how cells render by supplying a formatter function,
either for all tables with the :confval:`enum_table_formatter` configuration value or for a
single table with the :rst:dir:`enum-table:formatter` option. Formatters are passed the member,
the column name and the raw value. They may return text, a docutils node or ``None`` to fall back
to the default formatting:

.. literalinclude:: ./examples.py
   :language: python
   :start-after: # [formatter]
   :end-before: # [formatter]

.. code-block:: rst

   .. enum-table:: examples.Planet
      :formatter: examples.planet_formatter

.. enum-table:: examples.Planet
   :formatter: examples.planet_formatter

Downloads
=========

Tables can offer download buttons for CSV and JSON versions of their data. Downloads are off by
default. Turn them on for every table with :confval:`enum_table_download`:

.. code-block:: python

   # conf.py
   enum_table_download = True  # or a list of formats, e.g. ["json"]

HTML builders render the buttons below the table. Other builders (e.g. LaTeX/PDF, text and epub)
omit them. Tables render natively in every builder, including PDF.

* **CSV** files contain the header row and the display text of every cell, exactly as rendered.
* **JSON** files contain an object keyed by member name. Each member maps to an object keyed by
  column name (the ``name`` column is omitted since it is the key). Native JSON types (strings,
  numbers, booleans and ``null``) are preserved. Lists, tuples, dicts, dataclasses and named tuples
  are converted to their JSON equivalents, and any other values use their display text. For
  example:

  .. code-block:: json

     {
       "MERCURY": {"mass": 3.303e+23, "radius": 2439700.0, "moons": 0},
       "VENUS": {"mass": 4.869e+24, "radius": 6051800.0, "moons": 0}
     }

Use :rst:dir:`enum-table:download` to override the setting for a single table, either to add
downloads to a table when they are off globally or to remove them when they are on. Given without
a value it offers every format:

.. code-block:: rst

   .. enum-table:: examples.Planet
      :download:

   .. enum-table:: examples.Planet
      :download: json

   .. enum-table:: examples.Planet
      :download: none

.. _enum_properties:

enum-properties Enums
=====================

enum-properties_ enums are supported as a special case. Each declared property is rendered as a
column after the ``value`` column (and after any dataclass fields if the enum also mixes in a
dataclass). enum-properties is not a dependency of this extension. Its enums are detected
automatically. Docstrings on the property annotations describe their columns in the
:ref:`column legend <column_legend>`.

.. literalinclude:: ./examples.py
   :language: python
   :start-after: # [enum-properties]
   :end-before: # [enum-properties]

.. code-block:: rst

   .. enum-table:: examples.Shade
      :legend:

.. enum-table:: examples.Shade
   :legend:

Cross Referencing
=================

Give a table a :rst:dir:`enum-table:name` to reference it with :rst:role:`ref` or, when
:confval:`numfig <sphinx:numfig>` is enabled and the table has a caption, :rst:role:`numref`.

.. code-block:: rst

   .. enum-table:: examples.Planet
      :caption: The inner planets.
      :name: planets

   See :ref:`planets`.

Named tables are added to the project's intersphinx_ inventory as ``std:label`` entries, so
other projects can link to them too (e.g. ``:ref:`yourdocs:planets```). Tables without a name
are not in the inventory.

.. note::

   The directive only documents the enumeration as a table. It does not register the enum class
   or its members as Python objects, so roles like :rst:role:`py:class` and
   :rst:role:`py:attr` will not resolve to the table (locally or through intersphinx). Member
   names and enum-valued cells are rendered as text, not links. To make the enum and its members
   referenceable, also document them with :mod:`~sphinx.ext.autodoc` (e.g.
   :rst:dir:`autoclass`) and those references will resolve to the autodoc entries.
