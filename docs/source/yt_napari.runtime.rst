Dataset cache, configuration and logging
----------------------------------------

Dataset cache
*************

When the ``in_memory_cache`` configuration option is enabled (the default, see
:ref:`configfile`), the widgets and the JSON reader keep references to loaded
yt datasets in a module-level :class:`~yt_napari._ds_cache.DatasetCache` so
that repeated selections from the same dataset do not reload it. Large
datasets can be released from memory with
:meth:`~yt_napari._ds_cache.DatasetCache.rm_all`:

.. code-block:: python

    from yt_napari._ds_cache import dataset_cache
    dataset_cache.rm_all()

.. autodata:: yt_napari._ds_cache.dataset_cache
   :no-value:

.. autoclass:: yt_napari._ds_cache.DatasetCache
   :members:

Configuration
*************

yt-napari stores its options in a ``[yt_napari]`` section of the base yt
configuration (``yt.toml``). Importing :mod:`yt_napari.config` adds the section
and any missing defaults to the active ``yt.config.ytcfg`` instance, so options
can be read or changed at runtime with, e.g.,
``ytcfg.get("yt_napari", "in_memory_cache")``. The available options and their
defaults are listed in :ref:`configfile`.

.. automodule:: yt_napari.config
   :members:
   :undoc-members:

Logging
*******

yt-napari logs through the standard library :mod:`logging` module using a
logger named ``"yt_napari"``. To change the verbosity:

.. code-block:: python

    import logging
    from yt_napari.logging import ytnapari_log
    ytnapari_log.setLevel(logging.DEBUG)

.. autodata:: yt_napari.logging.ytnapari_log
   :no-value:
