Sample data
-----------

With the ``yt-napari[full]`` dependencies installed, a selection of the
`yt sample datasets <https://yt-project.org/data/>`_ can be loaded from the
napari GUI (``File -> Open Sample -> yt-napari``, see :ref:`sampledata`). Each
sample is loaded from a yt-napari JSON file bundled with the package that
describes a default field and selection. The first load of a sample downloads
the data with ``yt.load_sample``.

.. autofunction:: yt_napari._ds_cache.get_sample_set_list

.. autofunction:: yt_napari.sample_data._generic_loader.load_sample_data

Sample loaders
**************

The following functions back the napari ``sample_data`` contributions. The
module is generated from the sample registry by ``task update_sample_data``
(see ``repo_utilities/update_sample_data.py``); do not edit it directly.

.. automodule:: yt_napari.sample_data._sample_data
   :members:
   :undoc-members:
