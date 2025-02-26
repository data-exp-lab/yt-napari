import napari
import yt
from magicgui import widgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT as NavigationToolbar,
)
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from yt_napari._gui_utilities import clearLayout
from yt_napari.viewer import layers_to_yt


class YTPhasePlot(QWidget):
    def __init__(self, napari_viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = napari_viewer
        root_vbox = QVBoxLayout()

        active_layers = self.available_layer_list
        self.current_layers = active_layers
        self.add_layer_dropdown("layer_1", "x field", root_vbox)
        self.add_layer_dropdown("layer_2", "y field", root_vbox)
        self.add_layer_dropdown("layer_3", "z field", root_vbox)
        self.add_layer_dropdown(
            "layer_4_weight", "weight_field", root_vbox, allow_none=True, value="None"
        )

        sub_QVbox = QVBoxLayout()
        update_layers = widgets.PushButton(text="Refresh layers")
        update_layers.clicked.connect(self.update_available_layers)
        self.update_layers = update_layers
        sub_QVbox.addWidget(self.update_layers.native)

        self.callback_container = QVBoxLayout()
        _cmap_choices = _get_cmap_choices()

        cmaps = widgets.Dropdown(value=_cmap_choices[0], choices=_cmap_choices)
        self.callback_cmap = cmaps
        self.callback_cmap_reverse = widgets.CheckBox(value=False, text="reverse cmap")
        self.callback_container.addWidget(cmaps.native)
        self.callback_container.addWidget(self.callback_cmap_reverse.native)
        self.callback_logx = widgets.CheckBox(value=False, text="log x field")
        self.callback_logy = widgets.CheckBox(value=False, text="log y field")
        self.callback_logz = widgets.CheckBox(value=False, text="log z field")
        qh = QHBoxLayout()
        qh.addWidget(self.callback_logx.native)
        qh.addWidget(self.callback_logy.native)
        qh.addWidget(self.callback_logz.native)
        self.callback_container.addLayout(qh)
        sub_QVbox.addLayout(self.callback_container)

        self.render_button = widgets.PushButton(text="Render")
        self.render_button.clicked.connect(self.render_phaseplot)
        sub_QVbox.addWidget(self.render_button.native)

        self.phaseplot_container = QVBoxLayout()
        self.phaseplot_container.addWidget(QLabel(text="Click render to generate plot"))
        sub_QVbox.addLayout(self.phaseplot_container)

        root_vbox.addLayout(sub_QVbox)
        self.setLayout(root_vbox)

        self._phase_plot_ds = None
        self.phase_plot = None
        self.fig = None
        self.canvas = None

    def add_layer_dropdown(
        self,
        layer_attr: str,
        layer_label: str,
        root_qt_layout: QVBoxLayout,
        value: str = None,
        allow_none: bool = False,
    ):

        layer_hbox = QHBoxLayout()
        active_layers = self.available_layer_list
        if allow_none:
            active_layers = [
                "None",
            ] + active_layers

        if value is None:
            value = active_layers[0]

        layer_hbox.addWidget(QLabel(layer_label))
        new_box: QComboBox = widgets.ComboBox(
            value=value, choices=active_layers, name=layer_label
        ).native
        setattr(self, layer_attr, new_box)

        layer_hbox.addWidget(getattr(self, layer_attr))
        root_qt_layout.addLayout(layer_hbox)

    @staticmethod
    def reset_layer_combobox(combobox: QComboBox, new_layers: list[str]):
        combobox.clear()
        combobox.addItems(new_layers)
        combobox.setCurrentIndex(0)

    def update_available_layers(self):
        layers = self.available_layer_list
        self.current_layers = layers

        for combobox in (self.layer_1, self.layer_2, self.layer_3):
            self.reset_layer_combobox(combobox, layers)

        layers = [
            "None",
        ] + layers
        self.reset_layer_combobox(self.layer_4_weight, layers)

    def render_phaseplot(self):

        layer1 = self.current_layers[self.layer_1.currentIndex()]
        layer2 = self.current_layers[self.layer_2.currentIndex()]
        layer3 = self.current_layers[self.layer_3.currentIndex()]
        wt_field = self.current_layers[self.layer_4_weight.currentIndex()]
        if wt_field == "None":
            wt_field = None

        layers = [layer1, layer2, layer3, wt_field]
        layers_for_yt = []
        pp_args = []
        for layer in layers:
            if _is_index_field(layer):
                pp_args.append(("index", layer))
            elif layer is not None:
                pp_args.append(("stream", layer))
                layers_for_yt.append(layer)
            else:
                pp_args.append(None)

        ds = layers_to_yt(self.viewer, layers=layers_for_yt, axis_order=("z", "y", "x"))

        pp = yt.PhasePlot(
            ds,
            pp_args[0],
            pp_args[1],
            pp_args[2],
            weight_field=pp_args[3],
        )

        self._phase_plot_ds = ds
        self.phase_plot = pp
        self._phase_plot_field_args = pp_args
        self.fig = pp.plots[pp.fields[0]].figure

        # the callbacks
        cmap_value = _validate_cmyt_name(self.callback_cmap.value)
        if self.callback_cmap_reverse.value is True:
            cmap_value += "_r"

        pp_zfield = self._phase_plot_field_args[2]
        pp.set_cmap(pp_zfield, cmap_value)

        pp.set_log(pp_args[0], self.callback_logx.value)
        pp.set_log(pp_args[1], self.callback_logy.value)
        pp.set_log(pp_args[2], self.callback_logz.value)

        # finally, render it
        pp.render()

        # and add it to the layout
        clearLayout(self.phaseplot_container)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.draw()
        nt = NavigationToolbar(self.canvas)
        self.phaseplot_container.addWidget(nt)
        self.phaseplot_container.addWidget(self.canvas)

    @property
    def available_layer_list(self):
        layers = [layer.name for layer in self.viewer.layers]

        dims = ["x", "y", "z", "ones"]  # TODO: check ndim
        layers += dims
        return layers


def _is_index_field(layer_name: str):
    return layer_name in ("x", "y", "z", "ones")


def _get_cmap_choices() -> list[str]:
    import cmyt
    from matplotlib.colors import Colormap

    cmaps = [
        "arbre",
        "viridis",
        "magma",
        "doom",
        "cividis",
        "plasma",
        "RdBu",
        "coolwarm",
    ]

    # we want to display colormap name then cmyt for sorting purposes
    cmyt_names = [
        f"{cm}.cmyt"
        for cm in dir(cmyt)
        if isinstance(getattr(cmyt, cm), Colormap) and cm.endswith("_r") is False
    ]

    cmaps = cmaps + cmyt_names
    cmaps.sort(key=lambda v: v.lower())
    return cmaps


def _validate_cmyt_name(cm):
    if cm.endswith(".cmyt"):
        return "cmyt." + cm.split(".")[0]
    return cm
