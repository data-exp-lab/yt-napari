from typing import Callable, Optional

import napari
from magicgui import widgets
from qtpy import QtCore
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QAbstractItemView,
    QListView,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from yt_napari import _data_model, _gui_utilities, _model_ingestor


class MetadataWidget(QWidget):
    def __init__(self, napari_viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.viewer = napari_viewer

        self.big_container = widgets.Container()
        self.metadata_input_container = _gui_utilities.get_yt_metadata_container()
        self.big_container.append(self.metadata_input_container)
        self._post_load_function: Optional[Callable] = None

        pb = widgets.PushButton(text="Inspect")
        pb.clicked.connect(self.inspect_file)
        self.big_container.append(pb)

        self.meta_data_display = widgets.Container()
        self.big_container.append(self.meta_data_display)
        self.layout().addWidget(self.big_container.native)
        self.list_widgets = None

    def inspect_file(self):
        if self.list_widgets is not None:
            for list_widget in self.list_widgets.values():
                self.layout().removeWidget(list_widget)
                list_widget.setParent(None)

        py_kwargs = {}
        _gui_utilities.translator.get_pydantic_kwargs(
            self.metadata_input_container, _data_model.MetadataModel, py_kwargs
        )

        # instantiate the base model
        model = _data_model.MetadataModel.parse_obj(py_kwargs)

        # process it!
        fields_by_type = _model_ingestor._process_metadata_model(model)

        list_widgets = {}
        ilist = 0
        for ftype, fields in fields_by_type.items():
            list_widgets[ftype] = LayersList(ftype, fields, ilist < 3)
            ilist += 1
            self.layout().addWidget(list_widgets[ftype])

        self.list_widgets = list_widgets


# based on answer here:
# https://stackoverflow.com/questions/11077793/is-there-a-standard-component-for-collapsible-panel-in-qt


class CustomQStandardItem(QStandardItem):
    def __init__(self, icon, text):
        super().__init__(icon, text)

    def dropMimeData(self, data, action, row, column, parent):
        pass


class LayersList(QWidget):
    """
    LayerList class which acts as collapsable list.
    """

    def __init__(self, name, layers, expand=True):
        super().__init__()
        self.currently_expanded = True
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.expand_button = QPushButton(name)
        self.expand_button.setToolTip(f"List of {name} Layers")
        self.layer_list = QListView()
        self.layer_list.setDragEnabled(True)
        self.container_model = QStandardItemModel()
        for layer in layers:
            layer_label = QStandardItem(layer)
            self.container_model.appendRow(layer_label)
        self.layer_list.setModel(self.container_model)
        self.layer_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.main_layout.addWidget(self.expand_button)
        self.main_layout.addWidget(self.layer_list)
        self.expand_button.clicked.connect(self.expand)
        self.setLayout(self.main_layout)
        self.resized_size = 16.5 * len(layers)
        if not expand:
            self.expand()

    @QtCore.Slot()
    def expand(self):
        if self.currently_expanded:
            self.layer_list.setMaximumHeight(0)
            self.currently_expanded = False
        else:
            self.layer_list.setMaximumHeight(self.resized_size)
            self.currently_expanded = True
