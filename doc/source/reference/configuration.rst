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

   # only offer json downloads
   enum_table_download = ["json"]

   # format cells with a custom function
   enum_table_formatter = "mypackage.docs.format_cell"

.. confval:: enum_table_download
   :type: ``list[str]``
   :default: ``["csv", "json"]``

   The download formats to offer beneath every table. Set to an empty list to disable downloads.
   Can be overridden per table with :rst:dir:`enum-table:download`.

.. confval:: enum_table_formatter
   :type: ``str | Callable | None``
   :default: ``None``

   A function, or the import path of a function, used to format every table cell. See
   :data:`~sphinxcontrib_enum.Formatter`. Import paths are preferred because Sphinx cannot cache
   function configuration values between builds. Can be overridden per table with
   :rst:dir:`enum-table:formatter`.
