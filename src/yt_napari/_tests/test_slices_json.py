from yt_napari._data_model import InputModel
from yt_napari._model_ingestor import _choose_ref_layer, _process_validated_model

jdict = {
    "$schema": "yt-napari_0.0.2.json",
    "data": [
        {
            "filename": "_ytnapari_load_grid",
            "selections": {
                "slices": [
                    {
                        "fields": [{"field_name": "density", "field_type": "gas"}],
                        "resolution": [400, 400],
                        "normal": "x",
                        "slice_width": {"value": 0.25, "unit": "code_length"},
                        "slice_height": {"value": 0.25, "unit": "code_length"},
                        "center": {"value": [0.5, 0.5, 0.5], "unit": "code_length"},
                    }
                ]
            },
        }
    ],
}


def test_basic_slice_validation():
    _ = InputModel.parse_obj(jdict)


def test_slice_load(yt_ugrid_ds_fn):
    im = InputModel.parse_obj(jdict)
    layer_lists = _process_validated_model(im)
    ref_layer = _choose_ref_layer(layer_lists)
    _ = ref_layer.align_sanitize_layers(layer_lists)
