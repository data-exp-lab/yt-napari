# yt-napari

[![License](https://img.shields.io/pypi/l/yt-napari.svg?color=green)](https://github.com/data-exp-lab/yt-napari/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/yt-napari.svg?color=green)](https://pypi.org/project/yt-napari)
[![Python Version](https://img.shields.io/pypi/pyversions/yt-napari.svg?color=green)](https://python.org)
[![tests](https://github.com/data-exp-lab/yt-napari/workflows/tests/badge.svg)](https://github.com/data-exp-lab/yt-napari/actions)
[![codecov](https://codecov.io/gh/data-exp-lab/yt-napari/branch/main/graph/badge.svg)](https://codecov.io/gh/data-exp-lab/yt-napari)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/yt-napari)](https://napari-hub.org/plugins/yt-napari)

A napari plugin for loading data from yt

----------------------------------

This [napari] plugin was generated with [Cookiecutter] using [@napari]'s [cookiecutter-napari-plugin] template.

<!--
Don't miss the full getting started guide to set up your new package:
https://github.com/napari/cookiecutter-napari-plugin#getting-started

and review the napari docs for plugin developers:
https://napari.org/plugins/stable/index.html
-->

## Installation

This plugin is built for napari's new plugin engine, `npe2`. At present this requires a couple of manual installation steps:

1. install napari from source:

    git clone https://github.com/napari/napari
    cd napari
    pip install .[all]

2. install `npe2`:

    pip install npe2

You can install `yt-napari` via [pip]:

    pip install yt-napari


To install latest development version :

    pip install git+https://github.com/data-exp-lab/yt-napari.git


## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"yt-napari" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin

[file an issue]: https://github.com/data-exp-lab/yt-napari/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
