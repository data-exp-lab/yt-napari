## v0.6.1.dev

## v0.6.0

This release adds sample data loading and drops support for Python 3.10.

### New Features
* sample data: a selection of yt sample datasets can be loaded from the napari GUI via `File -> Open Sample -> yt-napari` ([#149](https://github.com/data-exp-lab/yt-napari/pull/149))

### Bug fixes
* ship the sample data and schema JSON files in the wheel (fixes import errors in non-editable installs and the empty API docs pages, [#161](https://github.com/data-exp-lab/yt-napari/issues/161), [#197](https://github.com/data-exp-lab/yt-napari/pull/197))
* disable yt logging during tests that use `yt_ugrid_ds_fn` ([#182](https://github.com/data-exp-lab/yt-napari/pull/182))

### Documentation
* extend the API reference ([#197](https://github.com/data-exp-lab/yt-napari/pull/197))
* update the images in notebooks 1 and 2 ([#147](https://github.com/data-exp-lab/yt-napari/pull/147))

### Maintenance
* drop Python 3.10, test on 3.11-3.14, and switch CI to PyQt6 ([#151](https://github.com/data-exp-lab/yt-napari/pull/151), [#187](https://github.com/data-exp-lab/yt-napari/pull/187), [#196](https://github.com/data-exp-lab/yt-napari/pull/196))
* move packaging config from setup.cfg/setup.py to pyproject.toml ([#198](https://github.com/data-exp-lab/yt-napari/pull/198))
* replace flake8, autoflake, isort, and black with ruff in pre-commit, enable the bugbear and pyupgrade rules, and lint the example notebooks ([#193](https://github.com/data-exp-lab/yt-napari/pull/193), [#194](https://github.com/data-exp-lab/yt-napari/pull/194), [#195](https://github.com/data-exp-lab/yt-napari/pull/195))
* add a dependabot configuration ([#189](https://github.com/data-exp-lab/yt-napari/pull/189))
* add a `task test` command to run the test suite ([#150](https://github.com/data-exp-lab/yt-napari/pull/150))
* simplify complex index ([#146](https://github.com/data-exp-lab/yt-napari/pull/146))

## v0.5.0

### New Features
* covering grid support ([#120](https://github.com/data-exp-lab/yt-napari/pull/120))

### Maintenance
* replace np.random.random with new Generator api ([#130](https://github.com/data-exp-lab/yt-napari/pull/130))


## v0.4.0
This release upgrades required dependencies:
* napari >= 0.4.19
* pydantic>2.0

## v0.3.0

This release introduces an initial metadata explorer widget and improvements to the
Reader widgets.

### New Features
* Saving Reader widget selections to yt-napari JSON ([#108](https://github.com/data-exp-lab/yt-napari/pull/108), @TomasPetro)
* Metadata explorer widget: check fields available in a dataset

## v0.2.1

Bugfix release.

### Fixes
* fix slice scaling for width!=height

## v0.2.0

This release includes some non-backwards compatible changes to the schema. Old
json files will need to be updated to use with yt-napari >= v0.2.0

### New Features
* timeseries loading: a new widget, yt-napari timeseries slicer, is available from the napari gui and json files can also specify timeseries selections. Additionally, there is a new `yt_napari.timeseries` module for jupyter notebook interaction.

### Breaking changes

Breaking schema updates:
* the top level `data` attribute has been renamed `datasets` to distinguish between loading selections from a single timestep and the new `timeseries` selection

## v0.1.0

This release includes some non-backwards compatible changes to the schema. Old
json files will need to be updated. The main change is that with the addition of
adding 2D slices, the region selection from v0.0.1 has been nested within a
`SelectionObject` level.

### New Features

* can now load 2D slices
* widget reader redesign: add multiple selections!
* yt dataset cacheing to speed up subsequent loads
* improved logging
* test infrastructure updates
* improved development maintenance scripts
