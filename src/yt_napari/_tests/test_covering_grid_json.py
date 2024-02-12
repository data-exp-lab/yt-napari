import pytest

from yt_napari._data_model import InputModel
from yt_napari._model_ingestor import _choose_ref_layer, _process_validated_model
from yt_napari._schema_version import schema_name

jdicts = []
jdicts.append(
    {
        "$schema": schema_name,
        "datasets": [
            {
                "filename": "_ytnapari_load_grid",
                "selections": {
                    "covering_grids": [
                        {
                            "fields": [{"field_name": "density", "field_type": "gas"}],
                            "left_edge": {"value": (0.4, 0.4, 0.4)},
                            "right_edge": {"value": (0.5, 0.5, 0.5)},
                            "level": 0,
                            "rescale": 1,
                        }
                    ]
                },
            }
        ],
    }
)


@pytest.mark.parametrize("jdict", jdicts)
def test_covering_grid_validation(jdict):
    _ = InputModel.model_validate(jdict)


@pytest.mark.parametrize("jdict", jdicts)
def test_slice_load(yt_ugrid_ds_fn, jdict):
    im = InputModel.model_validate(jdict)
    layer_lists, _ = _process_validated_model(im)
    ref_layer = _choose_ref_layer(layer_lists)
    _ = ref_layer.align_sanitize_layers(layer_lists)

    im_data = layer_lists[0][0]
    assert im_data.min() == 0
    assert im_data.max() == 1
