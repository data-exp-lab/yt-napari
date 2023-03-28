import logging

ytnapari_log = logging.getLogger("yt_napari")
ytnapari_log.setLevel(logging.INFO)

_formatter = logging.Formatter("%(name)s : [%(levelname)s ] %(asctime)s:  %(message)s")

_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_formatter)
ytnapari_log.addHandler(_stream_handler)
