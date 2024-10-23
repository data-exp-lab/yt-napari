# this file is autogenerated byt the taskipy update_sample data task
# to re-generate it, along with all the json files in this dir, run:
#     task update_sample_data
# (requires taskipy: pip install taskipy)
# do NOT edit this file directly, instead go modify
# repo_utilities/update_sample_data.py and then re-run the task.
from typing import List

from yt_napari._types import Layer
from yt_napari.sample_data import _generic_loader as gl


def sample_deeplynestedzoom() -> List[Layer]:
    return gl.load_sample_data("DeeplyNestedZoom")


def sample_enzo_64() -> List[Layer]:
    return gl.load_sample_data("Enzo_64")


def sample_galaxyclustermerger() -> List[Layer]:
    return gl.load_sample_data("GalaxyClusterMerger")


def sample_gaussiancloud() -> List[Layer]:
    return gl.load_sample_data("GaussianCloud")


def sample_hiresisolatedgalaxy() -> List[Layer]:
    return gl.load_sample_data("HiresIsolatedGalaxy")


def sample_isolatedgalaxy() -> List[Layer]:
    return gl.load_sample_data("IsolatedGalaxy")


def sample_popiii_mini() -> List[Layer]:
    return gl.load_sample_data("PopIII_mini")


def sample_smartstars() -> List[Layer]:
    return gl.load_sample_data("SmartStars")


def sample_cm1_tornado_lofs() -> List[Layer]:
    return gl.load_sample_data("cm1_tornado_lofs")
