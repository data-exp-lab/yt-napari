from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from yt_napari._model_ingestor import LayerDomain

# define types for the napari layer tuples
Layer = tuple[np.ndarray, dict, str]
SpatialLayer = tuple[np.ndarray, dict, str, "LayerDomain"]
