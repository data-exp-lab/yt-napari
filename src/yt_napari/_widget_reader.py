from collections import defaultdict
from typing import Callable, Optional

import napari
from magicgui import widgets
from napari.qt.threading import thread_worker
from qtpy import QtCore
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from yt_napari import _data_model, _gui_utilities, _model_ingestor
from yt_napari._ds_cache import dataset_cache
from yt_napari.viewer import _check_for_reference_layer


class YTReader(QWidget):

    _pydantic_model = None

    def __init__(self, napari_viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.viewer = napari_viewer
        self._post_load_function: Optional[Callable] = None

        self.add_dataset_selection_widget()
        self.add_spatial_selection_widgets()
        self.add_load_group_widgets()

    def add_dataset_selection_widget(self):
        self.ds_container = _gui_utilities.get_yt_data_container(
            ignore_attrs="selections", pydantic_model_class=self._pydantic_model
        )
        self.layout().addWidget(self.ds_container.native)

    def add_spatial_selection_widgets(self):
        # click button to add layer
        addition_group_layout = QHBoxLayout()
        add_new_button = widgets.PushButton(text="Click to add new selection")
        add_new_button.clicked.connect(self.add_a_selection)
        self.add_new_button = add_new_button.native
        addition_group_layout.addWidget(self.add_new_button)

        new_selection_type = QComboBox()
        new_selection_type.insertItems(0, _gui_utilities._valid_selections)
        self.new_selection_type = new_selection_type
        addition_group_layout.addWidget(self.new_selection_type)
        self.layout().addLayout(addition_group_layout)

        # the active selections, populated by add_a_selection
        self.active_selections = {}
        self.active_selection_types = {}
        self.active_selection_layout = QVBoxLayout()
        self.widg_id = 0
        self.layout().addLayout(self.active_selection_layout)

        # removing selections
        removal_group_layout = QHBoxLayout()

        rm_sel = widgets.PushButton(text="Delete Selection")
        rm_sel.clicked.connect(self.remove_selection)
        self.layer_deletion_button = rm_sel.native
        removal_group_layout.addWidget(self.layer_deletion_button)

        active_sel_list = QComboBox()
        active_sel_list.insertItems(0, list(self.active_selections.keys()))
        self.active_sel_list = active_sel_list
        removal_group_layout.addWidget(active_sel_list)

        self.layout().addLayout(removal_group_layout)

    def add_load_group_widgets(self):
        pass

    def add_a_selection(self):
        selection_type = self.new_selection_type.currentText()
        new_widg_id = self.widg_id + 1
        self.widg_id = new_widg_id
        widget_name = f"Selection {new_widg_id}, {selection_type}"
        widg_key = f"{selection_type}_{new_widg_id}"
        new_selection_widget = SelectionEntry(widget_name, selection_type)
        self.active_selections[widg_key] = new_selection_widget
        self.active_selection_layout.addWidget(self.active_selections[widg_key])
        self.active_sel_list.insertItem(new_widg_id - 1, widg_key.replace("_", " "))
        # the active_selection_types mapping lists dont need to be cleared
        self.active_selection_types[widg_key] = selection_type

    def remove_selection(self):
        widget_to_rm = self.active_sel_list.currentText().replace(" ", "_")
        if widget_to_rm is not None and widget_to_rm in self.active_selections:
            self.layout().removeWidget(self.active_selections[widget_to_rm])
            self.active_selections.pop(widget_to_rm)
            self.active_sel_list.clear()
            self.active_sel_list.insertItems(0, list(self.active_selections.keys()))


class ReaderWidget(YTReader):

    _pydantic_model = _data_model.DataContainer

    def add_load_group_widgets(self):
        load_group = QHBoxLayout()
        pb = widgets.PushButton(text="Load Selections")
        pb.clicked.connect(self.load_data)
        load_group.addWidget(pb.native)

        cc = widgets.PushButton(text="Clear cache")
        cc.clicked.connect(self.clear_cache)
        load_group.addWidget(cc.native)
        self.layout().addLayout(load_group)

    def clear_cache(self):
        dataset_cache.rm_all()

    def load_data(self):
        # this function semi-automatically extracts the arguments needed to
        # instantiate pydantic objects, which are then handed off to the
        # same data ingestion function as the json loader.

        # first, get the pydantic args for each selection type, embed in lists
        selections_by_type = defaultdict(list)
        for selection in self.active_selections.values():
            py_kwargs = selection.get_current_pydantic_kwargs()
            sel_key = selection.selection_type.lower() + "s"
            selections_by_type[sel_key].append(py_kwargs)

        # next, process remaining arguments (skipping selections):
        py_kwargs = {}
        _gui_utilities.translator.get_pydantic_kwargs(
            self.ds_container,
            self._pydantic_model,
            py_kwargs,
            ignore_attrs="selections",
        )

        # add selections in
        py_kwargs["selections"] = selections_by_type

        # now ready to instantiate the base model
        py_kwargs = {
            "datasets": [
                py_kwargs,
            ]
        }
        model = _data_model.InputModel.parse_obj(py_kwargs)

        # process each layer
        layer_list, _ = _model_ingestor._process_validated_model(model)

        # align all layers after checking for or setting the reference layer
        ref_layer = _check_for_reference_layer(self.viewer.layers)
        if ref_layer is None:
            ref_layer = _model_ingestor._choose_ref_layer(layer_list)
        layer_list = ref_layer.align_sanitize_layers(layer_list)

        for new_layer in layer_list:
            im_arr, im_kwargs, _ = new_layer
            if self._post_load_function is not None:
                im_arr = self._post_load_function(im_arr)

            # add the new layer
            self.viewer.add_image(im_arr, **im_kwargs)


class SelectionEntry(QWidget):
    """
    LayerList class which acts as collapsable list.
    """

    def __init__(self, name, selection_type: str, expand: bool = True):
        super().__init__()
        self.currently_expanded = True
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.expand_button = QPushButton(f"Selection {name}")
        self.expand_button.setToolTip(f"show/hide {name}")

        self.selection_container_raw = _gui_utilities.get_yt_selection_container(
            selection_type, return_native=False
        )
        self.selection_type = selection_type
        self.selection_container = self.selection_container_raw.native

        self.main_layout.addWidget(self.expand_button)
        self.main_layout.addWidget(self.selection_container)
        self.expand_button.clicked.connect(self.expand)
        self.setLayout(self.main_layout)
        self.resized_size = 16.5 * 1
        if not expand:
            self.expand()

    @QtCore.Slot()
    def expand(self):
        if self.currently_expanded:
            self.selection_container.hide()
            self.currently_expanded = False
        else:
            self.selection_container.show()
            self.currently_expanded = True

    def get_current_pydantic_kwargs(self) -> dict:
        # returns the pydantic instantiation dict for the current widget values
        py_kwargs = {}
        mgui_sel = self.selection_container_raw
        pydantic_model = getattr(_data_model, self.selection_type)
        _gui_utilities.translator.get_pydantic_kwargs(
            mgui_sel, pydantic_model, py_kwargs
        )
        return py_kwargs


_use_threading = True


class TimeSeriesReader(YTReader):
    _pydantic_model = _data_model.Timeseries

    def add_load_group_widgets(self):

        # the load and clear buttons
        load_group = QHBoxLayout()

        pb = widgets.PushButton(text="Load Selections")
        pb.clicked.connect(self.load_data)
        load_group.addWidget(pb.native)
        self.layout().addLayout(load_group)

    def load_data(self):

        # first, get the pydantic args for each selection type, embed in lists
        selections_by_type = defaultdict(list)
        for selection in self.active_selections.values():
            py_kwargs = selection.get_current_pydantic_kwargs()
            sel_key = selection.selection_type.lower() + "s"
            selections_by_type[sel_key].append(py_kwargs)

        # next, process remaining arguments (skipping selections):
        py_kwargs = {}
        _gui_utilities.translator.get_pydantic_kwargs(
            self.ds_container,
            self._pydantic_model,
            py_kwargs,
            ignore_attrs="selections",
        )

        if py_kwargs["file_selection"]["file_pattern"] == "":
            py_kwargs["file_selection"]["file_pattern"] = None

        if py_kwargs["file_selection"]["file_list"] == [""]:
            py_kwargs["file_selection"]["file_list"] = None

        if py_kwargs["file_selection"]["file_range"] == (0, 0, 0):
            py_kwargs["file_selection"]["file_range"] = None

        # add selections in
        py_kwargs["selections"] = selections_by_type

        # now ready to instantiate the base model
        py_kwargs = {
            "timeseries": [
                py_kwargs,
            ]
        }

        model = _data_model.InputModel.parse_obj(py_kwargs)

        if _use_threading:
            worker = time_series_load(model)
            worker.returned.connect(self.process_timeseries_layers)
            worker.start()
        else:
            _, layer_list = _model_ingestor._process_validated_model(model)
            self.process_timeseries_layers(layer_list)

    def process_timeseries_layers(self, layer_list):
        for new_layer in layer_list:
            im_arr, im_kwargs, _ = new_layer
            # probably can remove since the _special_loaders can be used
            # if self._post_load_function is not None:
            #     im_arr = self._post_load_function(im_arr)
            # add the new layer
            self.viewer.add_image(im_arr, **im_kwargs)


@thread_worker(progress=True)
def time_series_load(model):
    _, layer_list = _model_ingestor._process_validated_model(model)
    return layer_list
