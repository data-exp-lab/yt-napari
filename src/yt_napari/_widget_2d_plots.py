import napari
import yt
from magicgui import widgets
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from qtpy.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget

from yt_napari._gui_utilities import clearLayout
from yt_napari.viewer import layers_to_yt


class YTPhasePlot(QWidget):
    def __init__(self, napari_viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.viewer = napari_viewer

        active_layers = self.available_layer_list
        self.current_layers = active_layers
        self.layer_1: QComboBox = widgets.ComboBox(
            value=active_layers[0], choices=active_layers, name="Layer 1"
        ).native
        self.layer_2: QComboBox = widgets.ComboBox(
            value=active_layers[0], choices=active_layers, name="Layer 2"
        ).native
        self.layer_3: QComboBox = widgets.ComboBox(
            value=active_layers[0], choices=active_layers, name="Layer 3"
        ).native

        self.layer_4_weight: QComboBox = widgets.ComboBox(
            value="None",
            choices=[
                "None",
            ]
            + active_layers,
            name="Layer 4",
        ).native

        self.layout().addWidget(self.layer_1)
        self.layout().addWidget(self.layer_2)
        self.layout().addWidget(self.layer_3)
        self.layout().addWidget(self.layer_4_weight)

        update_layers = widgets.PushButton(text="Refresh layers")
        update_layers.clicked.connect(self.update_available_layers)
        self.update_layers = update_layers
        self.layout().addWidget(self.update_layers.native)

        self.render_button = widgets.PushButton(text="Render")
        self.render_button.clicked.connect(self.render_phaseplot)
        self.layout().addWidget(self.render_button.native)

        self.phaseplot_container = QVBoxLayout()
        self.phaseplot_container.addWidget(QLabel(text="Click render to generate plot"))
        self.layout().addLayout(self.phaseplot_container)

        self.fig = None
        self.canvas = None

    def update_available_layers(self):
        print("update those layers")
        layers = self.available_layer_list
        # layers = list(zip(range(len(layers)), layers))
        self.current_layers = layers

        self.layer_1.clear()
        self.layer_1.addItems(layers)
        self.layer_1.setCurrentIndex(0)
        self.layer_2.clear()
        self.layer_2.addItems(layers)
        self.layer_2.setCurrentIndex(0)
        self.layer_3.clear()
        self.layer_3.addItems(layers)
        self.layer_3.setCurrentIndex(0)
        # weight field
        self.layer_4.clear()
        self.layer_4.addItems(
            [
                "None",
            ]
            + layers
        )
        self.layer_4.setCurrentIndex(0)

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
            print(layer)
            if _is_index_field(layer):
                pp_args.append(("index", layer))
            elif layer is not None:
                pp_args.append(("stream", layer))
                layers_for_yt.append(layer)
            else:
                pp_args.append(None)

        ds = layers_to_yt(self.viewer, layers_for_yt, axis_order=("z", "y", "x"))

        pp = yt.PhasePlot(
            ds,
            pp_args[0],
            pp_args[1],
            pp_args[2],
            weight_field=pp_args[3],
        )
        pp.render()

        clearLayout(self.phaseplot_container)

        self.fig = pp.plots[pp.fields[0]].figure
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.draw()
        self.phaseplot_container.addWidget(self.canvas)

    @property
    def available_layer_list(self):
        layers = [layer.name for layer in self.viewer.layers]

        dims = ["x", "y", "z", "ones"]  # TODO: check ndim
        layers += dims
        return layers


def _is_index_field(layer_name: str):
    return layer_name in ("x", "y", "z", "ones")
