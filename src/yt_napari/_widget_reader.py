from typing import Callable, Optional

import napari
from magicgui import widgets
from qtpy.QtWidgets import QVBoxLayout, QWidget

from yt_napari import _data_model, _gui_utilities, _model_ingestor
from yt_napari.viewer import Scene


class ReaderWidget(QWidget):
    def __init__(self, napari_viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.viewer = napari_viewer

        self.big_container = widgets.Container()
        self.data_container = _gui_utilities.get_yt_data_container()
        self.big_container.append(self.data_container)
        self._post_load_function: Optional[Callable] = None

        pb = widgets.PushButton(text="Load")
        pb.clicked.connect(self.load_data)
        self.big_container.append(pb)
        self.layout().addWidget(self.big_container.native)

    _yt_scene: Scene = None  # will persist across widget calls

    @property
    def yt_scene(self):
        if self._yt_scene is None:
            self._yt_scene = Scene()
        return self._yt_scene

    def load_data(self):
        # first extract all the pydantic arguments from the container
        py_kwargs = {}
        _gui_utilities.translator.get_pydantic_kwargs(
            self.data_container, _data_model.DataContainer, py_kwargs
        )
        # instantiate the base model
        py_kwargs = {
            "data": [
                py_kwargs,
            ]
        }
        model = _data_model.InputModel.parse_obj(py_kwargs)
        # process it!
        layer_list = _model_ingestor._process_validated_model(model)

        # get the reference layer, align the current new layer
        layer_domain = layer_list[0][3]
        ref_layer = self.yt_scene._get_reference_layer(
            self.viewer.layers, default_if_missing=layer_domain
        )
        data, im_kwargs, _ = ref_layer.align_sanitize_layer(layer_list[0])

        if self._post_load_function is not None:
            data = self._post_load_function(data)

        # set the metadata
        take_log = model.data[0].selections[0].fields[0].take_log
        md = _model_ingestor.create_metadata_dict(
            data, layer_domain, take_log, reference_layer=ref_layer
        )
        im_kwargs["metadata"] = md

        # add the new layer
        self.viewer.add_image(data, **im_kwargs)
