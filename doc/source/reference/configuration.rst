.. include:: ../refs.rst

.. _configuration:

=============
Configuration
=============

The following configuration values can be set in your
:doc:`Sphinx configuration file <sphinx:usage/configuration>`:

.. code-block:: python

   extensions = [
       "sphinxcontrib_enum",
   ]

   # offer csv and json downloads for every table (off by default)
   enum_table_download = True

   # or only offer json downloads
   enum_table_download = ["json"]

   # format cells with a custom function
   enum_table_formatter = "mypackage.docs.format_cell"

.. confval:: enum_table_download
   :type: ``bool | list[str] | str | None``
   :default: ``False``

   The download formats to offer beneath every table. Downloads are off by default.

   * ``False``, ``None`` or an empty list - no download buttons.
   * ``True`` - offer every supported format (``csv`` and ``json``).
   * A list of formats, e.g. ``["json"]`` or ``["csv", "json"]``, or the same as a comma
     separated string (``"csv, json"``). Buttons are rendered in the order given.

   Unsupported formats are a configuration error. Can be overridden per table with
   :rst:dir:`enum-table:download`, so individual tables can opt in or out.

.. confval:: enum_table_formatter
   :type: ``str | Callable | None``
   :default: ``None``

   A function, or the import path of a function, used to format every table cell. See
   :data:`~sphinxcontrib_enum.Formatter`. Import paths are preferred because Sphinx cannot cache
   function configuration values between builds. Can be overridden per table with
   :rst:dir:`enum-table:formatter`.
