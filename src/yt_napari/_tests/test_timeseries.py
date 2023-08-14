from yt_napari import _data_model as dm, _model_ingestor as mi


def test_timeseries_file_collection(tmp_path):

    ts_dir = tmp_path / "output_dir"
    ts_dir.mkdir()

    flist_actual = []
    nfiles = 8
    for tstep in range(0, nfiles):
        tstepstr = str(tstep).zfill(4)
        fname = f"_ytnapari_load_grid-{tstepstr}"
        newfi = ts_dir / fname
        newfi.touch()

        flist_actual.append(str(newfi))

    file_dir = str(ts_dir)
    tfs = dm.TimeSeriesFileSelection(
        file_pattern="_ytnapari_load_grid-????",
        directory=file_dir,
        # file_list=file_list,
        # file_range=file_range,
    )
    files = mi._find_timeseries_files(tfs)
    assert len(files) == nfiles
    assert all([fi in flist_actual for fi in files])

    tfs = dm.TimeSeriesFileSelection(
        directory=file_dir,
        file_list=flist_actual,
    )
    files = mi._find_timeseries_files(tfs)
    assert len(files) == nfiles
    assert all([fi in flist_actual for fi in files])

    tfs = dm.TimeSeriesFileSelection(
        file_pattern="_ytnapari_load_grid-????",
        directory=file_dir,
        file_range=(0, nfiles, 2),
    )
    files = mi._find_timeseries_files(tfs)
    assert len(files) == nfiles / 2
