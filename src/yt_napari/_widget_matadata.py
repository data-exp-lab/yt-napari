from typing import Callable, Optional

import napari
from magicgui import widgets
from qtpy import QtCore
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from unyt import unyt_array

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
        self.widgets_to_clear: list = None

    def inspect_file(self):
        if self.widgets_to_clear is not None:
            # always clear out the widgets when the button is pushed
            for list_widget in self.widgets_to_clear:
                self.layout().removeWidget(list_widget)
                list_widget.setParent(None)
        self.widgets_to_clear = []
        self.field_lists = {}
        self.array_vals = {}
        py_kwargs = {}

        _gui_utilities.translator.get_pydantic_kwargs(
            self.metadata_input_container, _data_model.MetadataModel, py_kwargs
        )

        # instantiate the base model
        model = _data_model.MetadataModel.parse_obj(py_kwargs)

        # process it!
        meta_data_dict, fields_by_type = _model_ingestor._process_metadata_model(model)

        # display the metadata
        for attr, val in meta_data_dict.items():
            if isinstance(val, unyt_array):
                newid = UnytArrayQWidget(attr, val)
                self.array_vals[attr] = newid
            else:
                newid = QLabel(f"{attr}: {str(val)}")
            self.widgets_to_clear.append(newid)
            self.layout().addWidget(newid)

        # the collapsible field display
        ilist = 0
        for ftype, fields in fields_by_type.items():
            new_field_list = LayersList(ftype, fields, ilist < 3)
            ilist += 1
            self.field_lists[ftype] = new_field_list
            self.widgets_to_clear.append(new_field_list)
            self.layout().addWidget(new_field_list)


# based on answer here:
# https://stackoverflow.com/questions/11077793/is-there-a-standard-component-for-collapsible-panel-in-qt


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
        self.resized_size = int(16 * len(layers))
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


class UnytArrayQWidget(QWidget):
    # based of of yt.units.display_ytarray() : simpler to rewrite it than try
    # to convert the ipywidget to Qt.
    def __init__(self, arr_name: str, arr: unyt_array):
        super().__init__()

        unit_registry = arr.units.registry
        self._unit_options = unit_registry.list_same_dimensions(arr.units)
        self.arr = arr.copy()
        self.arr_name = arr_name
        self.units_box = QComboBox()
        self.units_box.addItems(self._unit_options)
        self.units_box.setCurrentText(str(self.arr.units))
        self.units_box.currentTextChanged.connect(self.update_units)
        self.arr_display = QLabel(self._get_display_name_text())

        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(self.arr_display)
        self.main_layout.addWidget(self.units_box)
        self.setLayout(self.main_layout)

    def update_units(self, new_units_str):
        self.arr = self.arr.to(new_units_str)
        self.arr_display.setText(self._get_display_name_text())

    def _get_display_name_text(self):
        return f"{self.arr_name}: {str(self.arr.value)}"
