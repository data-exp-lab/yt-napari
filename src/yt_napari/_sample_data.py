import json

from yt_napari import __version__
from yt_napari._model_ingestor import load_from_json_strs

isogaldict = {
    "datasets": [
        {
            "filename": "IsolatedGalaxy",
            "selections": {
                "regions": [
                    {
                        "fields": [
                            {
                                "field_name": "Density",
                                "field_type": "enzo",
                                "take_log": True,
                            }
                        ],
                        "left_edge": {
                            "value": [
                                0.4,
                                0.4,
                                0.4,
                            ],
                            "unit": "Mpc",
                        },
                        "right_edge": {
                            "value": [
                                0.6,
                                0.6,
                                0.6,
                            ],
                            "unit": "Mpc",
                        },
                        "resolution": [400, 400, 400],
                    },
                ]
            },
            "edge_units": "Mpc",
        }
    ]
}


def isogal():
    isogaldict["$schema"] = f"yt-napari_{__version__}.json"
    json_objs = [json.dumps(isogaldict)]
    result = load_from_json_strs(json_objs)
    return result
