"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/plugins/stable/npe2_manifest_specification.html

Replace code below accordingly.  For complete documentation see:
https://napari.org/docs/dev/plugins/index.html
"""
# <-----temporary
# bad
from PyQt5 import QtWidgets
# ----->
import json

from yt_napari._data_model import InputModel


def napari_get_reader(path):
    """A basic implementation of a Reader contribution.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    function or None
        If the path is a recognized format, return a function that accepts the
        same path or list of paths, and returns a list of layer data tuples.
    """
    if isinstance(path, list):
        # reader plugins may be handed single path, or a list of paths.
        # if it is a list, it is assumed to be an image stack...
        # so we are only going to look at the first file.
        path = path[0]

    # if we know we cannot read the file, we immediately return None.
    if not path.endswith(".json"):
        return None

    with open(path) as jhandle:
        schema_raw = json.load(jhandle)
        schema_version = schema_raw.get("$schema", None)

    pfx = InputModel._schema_prefix
    if schema_version is None or pfx not in schema_version:
        # To Do: check schema against a list of valid schemas rather than a
        # single schema.
        # the schema does not match a known schema for this plugin
        return None

    # otherwise we return the *function* that can read ``path``.
    return reader_function


def reader_function(path):
    """Take a path or list of paths and return a list of LayerData tuples.

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_*
        method in napari, and layer_type is a lower-case string naming the
        type of layer. Both "meta", and "layer_type" are optional. napari
        will default to layer_type=="image" if not provided
    """
    from yt_napari._model_ingestor import load_from_json

    # handle both a string and a list of strings
    if not isinstance(path, str):
        raise NotImplementedError("schema loader only supports a single path")

    data = load_from_json(path)  # the data
    add_kwargs = {}  # optional kwargs for the viewer.add_* method
    layer_type = "image"  # optional, default is "image"
    return [(data, add_kwargs, layer_type)]
