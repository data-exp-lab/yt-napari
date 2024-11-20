import napari
import numpy as np
import yt
from magicgui import widgets
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget


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

        self.layout().addWidget(self.layer_1)
        self.layout().addWidget(self.layer_2)
        self.layout().addWidget(self.layer_3)

        update_layers = widgets.PushButton(text="Refresh layers")
        update_layers.clicked.connect(self.update_available_layers)
        self.update_layers = update_layers
        self.layout().addWidget(self.update_layers.native)

        self.phaseplot_container = QHBoxLayout()
        self.render_button = widgets.PushButton(text="Render")
        self.render_button.clicked.connect(self.render_phaseplot)
        self.phaseplot_container.addWidget(self.render_button.native)
        self.layout().addLayout(self.phaseplot_container)

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

        # add option for weight_field

    def render_phaseplot(self):

        layer1 = self.current_layers[self.layer_1.currentIndex()]
        layer2 = self.current_layers[self.layer_2.currentIndex()]
        layer3 = self.current_layers[self.layer_3.currentIndex()]

        print("get those layers")

        l1 = self.viewer.layers[layer1]
        l2 = self.viewer.layers[layer2]
        l3 = self.viewer.layers[layer3]

        data = {
            l1.name: l1.data,
            l2.name: l2.data,
            l3.name: l3.data,
        }

        dims = data[l1.name].shape
        bbox = np.array([[0, dims[idim]] for idim in range(len(dims))])
        ds = yt.load_uniform_grid(data, dims, bbox=bbox, length_unit=1)
        # TODO: adjust for when selecting x, y, z
        pp = yt.PhasePlot(
            ds,
            ("stream", l1.name),
            ("stream", l2.name),
            ("stream", l3.name),
            weight_field=None,
        )
        pp.render()
        print("rendered... need to put the image in the widget...")

    @property
    def available_layer_list(self):
        layers = [layer.name for layer in self.viewer.layers]

        dims = ["x", "y", "z"]  # TODO: check ndim
        layers += dims
        return layers
