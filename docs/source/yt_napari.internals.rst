Developer API
-------------

The objects on this page are internal to yt-napari and may change between
releases. They are documented here for contributors and for users who want to
understand how yt-napari aligns layers or who need to inspect the metadata that
yt-napari attaches to napari layers.

Layer alignment
***************

Every image layer that yt-napari adds to napari carries a ``metadata`` dict
created by :func:`~yt_napari._model_ingestor.create_metadata_dict`. The
``_layer_domain`` entry is a :class:`~yt_napari._model_ingestor.LayerDomain`
describing the physical extent of the layer and the ``_reference_layer`` entry
is the :class:`~yt_napari._model_ingestor.ReferenceLayer` that the layer's
napari ``scale`` and ``translate`` were computed against.

.. autofunction:: yt_napari._model_ingestor.create_metadata_dict

.. autoclass:: yt_napari._model_ingestor.LayerDomain
   :members:

.. autoclass:: yt_napari._model_ingestor.ReferenceLayer
   :members:

.. autoclass:: yt_napari._model_ingestor.PhysicalDomainTracker
   :members:

.. autoclass:: yt_napari._model_ingestor.TimeseriesContainer
   :members:

.. autofunction:: yt_napari._model_ingestor.selections_match

Data models
***********

The pydantic models that define the yt-napari JSON schema (rendered on
:doc:`the schema page <../schema>`) and that the widgets are built from.

.. automodule:: yt_napari._data_model
   :members:
   :undoc-members:
   :exclude-members: _data_model_list, model_config, model_fields, model_computed_fields

Schema management
*****************

.. autoclass:: yt_napari.schemas._manager.Manager
   :members:

Widget construction
*******************

.. autoclass:: yt_napari._gui_utilities.MagicPydanticRegistry
   :members:
