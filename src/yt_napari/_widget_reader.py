from typing import Union

import magicgui
import napari
import qtpy
from magicgui import magic_factory

# example_plugin.some_module
Widget = Union["magicgui.widgets.Widget", "qtpy.QtWidgets.QWidget"]
from yt_napari.viewer import Scene


# a manual reader to get things started
@magic_factory(call_button="Load")
def widget_factory(
    viewer: "napari.viewer.Viewer",
    filename: str,
    field_type: str,
    field_name: str,
    take_log: bool = True,
    left_x: float = 0.0,
    left_y: float = 0.0,
    left_z: float = 0.0,
    right_x: float = 1.0,
    right_y: float = 1.0,
    right_z: float = 1.0,
    res_x: int = 400,
    res_y: int = 400,
    res_z: int = 400,
    edge_units: str = "code_length",
):
    """Generate thresholded image.

    This pattern uses magicgui.magic_factory directly to turn a function
    into a callable that returns a widget.
    """
    # import yt here so that it is only imported when the plugin first
    # activates:

    import yt  # noqa: E402

    ds = yt.load(filename)

    scene = Scene()

    # instantiate the pydanctic model objects here

    # should refactor add_to_viewer to get the new layer data without adding
    # it to the viewer so that the widget can return a new layer rather than
    # internally modifying the viewer object (though it does seem to work)
    le = ds.arr((left_x, left_y, left_z), edge_units)
    re = ds.arr((right_x, right_y, right_z), edge_units)
    scene.add_to_viewer(
        viewer,
        ds,
        (field_type, field_name),
        take_log=take_log,
        resolution=(res_x, res_y, res_z),
        left_edge=le,
        right_edge=re,
    )
