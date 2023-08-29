import pytest

from yt_napari._data_model import InputModel
from yt_napari._model_ingestor import _process_validated_model
from yt_napari._schema_version import schema_name

jdicts = []
jdicts.append(
    {
        "$schema": schema_name,
        "datasets": [
            {
                "filename": "_ytnapari_load_grid",
                "selections": {
                    "regions": [
                        {
                            "fields": [{"field_name": "density", "field_type": "gas"}],
                            "resolution": [10, 10, 10],
                        }
                    ]
                },
            }
        ],
    }
)


@pytest.mark.parametrize("jdict", jdicts)
def test_load_region(jdict):
    jdict["datasets"][0]["selections"]["regions"][0]["rescale"] = True
    m = InputModel.parse_obj(jdict)
    layers, _ = _process_validated_model(m)
    im_data = layers[0][0]
    assert im_data.min() == 0.0
    assert im_data.max() == 1.0
