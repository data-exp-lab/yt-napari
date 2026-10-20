Loading yt-napari JSON programmatically
---------------------------------------

The napari reader plugin loads yt-napari JSON files (see :ref:`jsonload` and
:doc:`the schema <../schema>`) by calling the functions below. They can also be
called directly to load the same selections from a script or notebook, which is
useful for reproducing a GUI session or for adding layers that are aligned with
layers already loaded from JSON.

.. code-block:: python

    import napari
    from yt_napari._model_ingestor import load_from_json

    viewer = napari.Viewer()
    for data, kwargs, layer_type in load_from_json(["my_selection.json"]):
        viewer.add_image(data, **kwargs)

.. autofunction:: yt_napari._model_ingestor.load_from_json

.. autofunction:: yt_napari._model_ingestor.load_from_json_strs
