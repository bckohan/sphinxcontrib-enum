.. include:: ../refs.rst

.. _directive:

=========
Directive
=========

.. rst:directive:: enum-table

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

   The only required argument is the import path of the enumeration. The module may be separated
   from the class with a ``:`` (``pkg.module:Outer.Enum``) or dots may be used throughout
   (``pkg.module.Outer.Enum``). If the path cannot be imported on its own it is also tried relative
   to the current module set by :rst:dir:`py:currentmodule` or :rst:dir:`py:module`.

   Options that take lists accept comma or whitespace separated values.

   .. rst:directive:option:: columns: columns to render
      :type: list

      The columns to render, in order. The pseudo-columns ``name`` and ``value`` are the member's
      name and value. Any other column is an attribute (or dotted attribute path) of the member,
      falling back to its value. Defaults to ``name``, any dataclass fields, ``value`` (only when the
      values are not dataclasses or named tuples), and any enum-properties_ properties.

   .. rst:directive:option:: exclude: columns to drop
      :type: list

      Columns to remove from the rendered columns.

   .. rst:directive:option:: members: members to render
      :type: list

      The names of the members to render, in order. Defaults to all members in definition order.

   .. rst:directive:option:: exclude-members: members to drop
      :type: list

      The names of members to leave out of the table.

   .. rst:directive:option:: headers: column=Header pairs
      :type: comma separated list

      Override the header text of columns, for example ``:headers: mass=Mass, radius=Radius``.
      Headers default to the column name. Header text may not contain commas.

   .. rst:directive:option:: caption: table caption
      :type: text

      A caption for the table. Inline markup is supported.

   .. rst:directive:option:: name: reference label
      :type: text

      A label for cross referencing the table with :rst:role:`ref` or :rst:role:`numref`.

   .. rst:directive:option:: class: css classes
      :type: list

      Additional CSS classes to add to the table.

   .. rst:directive:option:: widths: column widths
      :type: auto, grid or a list of integers

      **default**: ``auto``

      Column widths. ``auto`` lets the writer size the columns, ``grid`` makes them equal and a
      list of integers gives the relative width of each column (it must have one entry per
      column).

   .. rst:directive:option:: download: download formats
      :type: list

      **default**: :confval:`enum_table_download`

      The download formats to offer for this table. Supports ``csv`` and ``json``, or ``none`` to
      disable downloads.

   .. rst:directive:option:: formatter: import path of a cell formatter
      :type: text

      **default**: :confval:`enum_table_formatter`

      The import path of a function to format cells for this table. See
      :data:`~sphinxcontrib_enum.Formatter`.
