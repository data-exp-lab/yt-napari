from yt_napari._widget_matadata import LayersList, MetadataWidget


def test_widget_reader(make_napari_viewer):
    viewer = make_napari_viewer()
    r = MetadataWidget(napari_viewer=viewer)
    r.metadata_input_container.filename.value = "_ytnapari_load_grid"
    r.inspect_file()
    r.inspect_file()  # do it again to hit that clear statement

    assert "stream" in r.field_lists.keys()

    r.field_lists["stream"].expand()
    r.field_lists["stream"].expand()

    assert "domain_left_edge" in r.array_vals.keys()
    r.array_vals["domain_left_edge"].update_units("km")
    r.deleteLater()


def test_layer_list():
    ll = LayersList("test_layer", range(0, 10), expand=False)
    ll.expand()
    assert ll.currently_expanded is True
    ll.deleteLater()
