import json

from yt_napari import __version__
from yt_napari._model_ingestor import load_from_json_strs


def load_sample_data(sample_name: str):

    json_file = f"sample_{sample_name.lower()}.json"

    import importlib.resources as importlib_resources

    jdata = json.loads(
        importlib_resources.files("yt_napari")
        .joinpath("sample_data")
        .joinpath(json_file)
        .read_bytes()
    )

    jdata["$schema"] = f"yt-napari_{__version__}.json"
    json_objs = [json.dumps(jdata)]
    result = load_from_json_strs(json_objs)
    return result
