import napari
from magicgui import widgets
from qtpy.QtWidgets import QVBoxLayout, QWidget

from yt_napari._data_model import DataContainer, InputModel
from yt_napari._gui_utilities import data_container, get_pydantic_kwargs
from yt_napari._model_ingestor import _process_validated_model


class ReaderWidget(QWidget):
    def __init__(self, napari_viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.viewer = napari_viewer

        # QCollapsible creates a collapse container for inner widgets
        self.big_container = widgets.Container()
        self.data_container = data_container
        self.big_container.append(self.data_container)

        pb = widgets.PushButton(text="Load")
        pb.clicked.connect(self.load_data)
        self.big_container.append(pb)
        self.layout().addWidget(self.big_container.native)

    def load_data(self):
        # first extract all the pydantic arguments from the container
        py_kwargs = {}
        get_pydantic_kwargs(self.data_container, DataContainer, py_kwargs)
        # instantiate the base model
        py_kwargs = {
            "data": [
                py_kwargs,
            ]
        }
        print(py_kwargs)
        model = InputModel.parse_obj(py_kwargs)
        # process it!
        layer_list = _process_validated_model(model)
        self.viewer.add_image(layer_list[0][0])
        # TODO: account for Scene!!!!
