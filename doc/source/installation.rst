.. include:: ./refs.rst

.. _installation:

============
Installation
============

.. code-block:: bash

   pip install sphinxcontrib-enum

To document enum-properties_ enums, install the ``properties`` extra, which installs a supported
version of enum-properties alongside the extension:

.. code-block:: bash

   pip install "sphinxcontrib-enum[properties]"

The extension does not import enum-properties itself, so any enum-properties enums that your
documentation can import are rendered either way. The extra only guarantees a compatible version.

And add the extension to your ``conf.py``:

.. code-block:: python

   extensions = [
       ...
       "sphinxcontrib_enum",
   ]
