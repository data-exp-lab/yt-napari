Quick Start
===========

After installation, there are three modes of using :code:`yt-napari`:

1. :ref:`jupyter notebook interaction<jupyusage>`
2. :ref:`loading a json file from the napari gui<jsonload>`
3. :ref:`napari gui plugins<naparigui>`

Additionally, you can configure some behavior between napari sessions: see  :ref:`Configuring yt-napari<configfile>`.

.. _jupyusage:

jupyter notebook interaction
****************************


:code:`yt-napari` provides a helper class, :code:`yt_napari.viewer.Scene` that assists in properly aligning new yt selections in the napari viewer when working in a Jupyter notebook.

.. code-block:: python

    import napari
    import yt
    from yt_napari.viewer import Scene
    from napari.utils import nbscreenshot

    viewer = napari.Viewer()
    ds = yt.load("IsolatedGalaxy/galaxy0030/galaxy0030")
    yt_scene = Scene()

    left_edge = ds.domain_center - ds.arr([40, 40, 40], 'kpc')
    right_edge = ds.domain_center + ds.arr([40, 40, 40], 'kpc')
    res = (600, 600, 600)

    yt_scene.add_region(viewer,
                        ds,
                        ("enzo", "Temperature"),
                        left_edge = left_edge,
                        right_edge = right_edge,
                        resolution = res)

    yt_scene.add_region(viewer,
                        ds,
                        ("enzo", "Density"),
                        left_edge = left_edge,
                        right_edge = right_edge,
                        resolution = res)


:code:`yt_scene.add_region` accepts any of the keyword arguments allowed by :code:`viewer.add_image`.

See :meth:`yt_napari.viewer.Scene` for all available methods and the :doc:`example notebooks <notebooks>` for further examples.

.. _jsonload:

loading a json file from the napari gui
***************************************

:code:`yt-napari` also provides the ability to load json directive files from the napari GUI as you would load any image file (:code:`File->Open`). The json file describes the selection process for a dataset as described by a json-schema. The following json file results in similar layers as the above notebook example

.. code-block:: json

    {"$schema": "https://yt-napari.readthedocs.io/en/latest/_static/yt-napari_latest.json",
     "datasets": [{"filename": "IsolatedGalaxy/galaxy0030/galaxy0030",
                   "selections": {"regions": [{
                                  "fields": [{"field_name": "Temperature", "field_type": "enzo", "take_log": true},
                                             {"field_name": "Density", "field_type": "enzo", "take_log": true}],
                                 "left_edge": {"value": [460.0, 460.0, 460.0], "unit": "kpc"},
                                 "right_edge": {"value": [560.0, 560.0, 560.0], "unit": "kpc"},
                                 "resolution": [600, 600, 600]
                              }]}
             }]
    }


Note that when live-editing the json in a development environment like vscode, you will get hints to help in filling out a json file. For example, in vscode, you will see field suggestions after specifying the `yt-napari` schema:

.. image:: _static/readme_ex_002_json.png


.. _naparigui:

napari widget plugins
*********************

In addition to the reader-plugin mentioned above, yt-napari includes a napari dock widget for loading in data selections from yt. If you have ideas for additional plugins, definitely reach out!

The yt-napari yt Reader:
########################

The use the yt Reader plugin, from a Napari viewer, select "Plugins -> yt-napari: yt Reader". Enter or select a file to load, fill out the remaining items to select a field and extent of the spatial selection, then hit load. yt-napari will then load the dataset, sample it and return a new napari image layer.

.. image:: _static/readme_ex_003_gui_reader.gif

The reader plugin does its best to align new selections of data with existing yt-napari image layers and should be able to properly align selections from different yt datasets (please submit a bug report if it fails!).


The yt-napari yt Time Series Reader:
####################################

This reader will apply a spatial selection to a set of files, similar to working with a yt `DataSeries` object. You specify
the spatial selections and a list of files or file pattern to match. Note that while the operation is in a non-blocking
thread, if your simulation data is large it may take a few minutes to load in your selections. Also note that 3D region
selections can easily exceed available memory if you're not careful... for improving load times and working with
bigger-than-memory arrays, you can instead use the jupyter notebook interface for napari with the `yt_napari.timeseries`
module of helper functions to distribute the timestep selections using dask. See the example notebooks for usage.

.. _configfile:

Configuring yt-napari
*********************

User options can be saved between napari sessions by adding to the base :code:`yt` configuration
file, :code:`yt.toml`. :code:`yt` looks for the configuration file in a number of places (check
out the :code:`yt` documentation
on `configuration <https://yt-project.org/doc/reference/configuration.html>`_ ). To add
:code:`yt-napari` options, open up (or create) the configuration file and add a
:code:`[yt_napari]` section. An example configuration file might look like:

.. code-block:: bash

    [yt]
    log_level = 1
    test_data_dir = "/path/to/yt_data"

    [yt_napari]
    in_memory_cache = true


Configuration options
#####################

The following options are available:

* :code:`in_memory_cache`, :code:`bool` (default :code:`true`). When :code:`true`,
the widget and json-readers will store references to yt datasets in an in-memory
cache. Subsequents loads of the same dataset will then use the available dataset
handle. This behavior can also be manually controlled in the widget and json
options -- changing it in the configuration will simply change the default value.


Note that boolean values in :code:`toml` files start with lowercase: :code:`true` and
:code:`false` (instead of :code:`True` and :code:`False`).
