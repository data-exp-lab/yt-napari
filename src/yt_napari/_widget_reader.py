from typing import Union

import magicgui
import napari
import qtpy
from magicgui import magic_factory
from qtpy.QtWidgets import QWidget

# example_plugin.some_module
Widget = Union["magicgui.widgets.Widget", "qtpy.QtWidgets.QWidget"]


class MyWidget(QWidget):
    """Any QtWidgets.QWidget or magicgui.widgets.Widget subclass can be used."""

    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)


@magic_factory
def widget_factory(
    image: "napari.types.ImageData", threshold: int
) -> "napari.types.LabelsData":
    """Generate thresholded image.

    This pattern uses magicgui.magic_factory directly to turn a function
    into a callable that returns a widget.
    """
    return (image > threshold).astype(int)


def threshold(
    image: "napari.types.ImageData", threshold: int
) -> "napari.types.LabelsData":
    """Generate thresholded image.

    This function will be turned into a widget using `autogenerate: true`.
    """
    return (image > threshold).astype(int)
