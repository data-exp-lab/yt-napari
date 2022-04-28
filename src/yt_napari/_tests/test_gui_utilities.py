from typing import List, Tuple, TypeVar

import pydantic
import pytest
from magicgui import type_map, widgets

from yt_napari import _gui_utilities as gu


def test_set_default():
    assert gu.set_default(1, None) == 1
    assert gu.set_default(None, 1) == 1


@pytest.fixture
def Model():
    class LowerModel(pydantic.BaseModel):
        field_a: float
        field_b: str = "field_b"

    class TestModel(pydantic.BaseModel):
        field_1: int = 1
        vec_field1: Tuple[float, float] = (1.0, 2.0)
        vec_field2: Tuple[float, float, float]
        bad_field: TypeVar("BadType")
        low_model: LowerModel
        multi_low_model: List[LowerModel]

    return TestModel


def test_registry(Model):
    reg = gu.MagicPydanticRegistry()

    assert reg.is_registered(Model, "field_1") is False
    with pytest.raises(KeyError):
        _ = reg.is_registered(Model, "field_2", required=True)

    def get_nested_container(nested_value, **kwargs):
        c = widgets.Container()
        cls, ops = type_map.get_widget_class(value=nested_value)
        ops.update(kwargs)
        print(ops)
        c.append(cls(value=nested_value, **ops))
        return c

    def get_value_from_nested(container_widget, extra_string):
        nested_val = [c.value for c in container_widget][0]
        return f"{nested_val}_{extra_string}"

    reg.register(
        Model,
        "field_1",
        magicgui_factory=get_nested_container,
        magicgui_args=(2,),
        magicgui_kwargs={"name": "testname"},
        pydantic_attr_factory=get_value_from_nested,
        pydantic_attr_args=("testxyz",),
    )

    widget_instance = reg.get_widget_instance(Model, "field_1")
    assert isinstance(widget_instance, widgets.Container)

    with pytest.raises(KeyError):
        reg.is_registered(Model, "missing_field", required=True)

    pyvalue = reg.get_pydantic_attr(Model, "field_1", widget_instance)
    assert pyvalue == "2_testxyz"


def test_yt_widget():

    file_editor = gu.get_file_widget(value="test")
    assert gu.get_filename(file_editor) == "test"

    values = gu.embed_in_list(file_editor)
    assert str(values[0]) == "test"


def test_pydantic_magicgui_default(Model):

    model_field = Model.__fields__["field_1"]
    c = gu.get_magicguidefault(model_field)
    assert c.value == model_field.default

    model_field = Model.__fields__["bad_field"]
    empty = gu.get_magicguidefault(model_field)
    assert isinstance(empty, widgets.EmptyWidget)

    tr = gu.MagicPydanticRegistry()
    c = widgets.Container()
    with pytest.warns(UserWarning):
        tr.add_pydantic_to_container(Model, c)


def test_pydantic_processing(Model):

    _ = gu._get_pydantic_model_field(Model, "field_1")

    tr = gu.MagicPydanticRegistry()

    def bad_container():
        return widgets.Container(name="bad_field")

    def get_bad_value(widget_instance):
        return widget_instance.name

    tr.register(
        Model,
        "bad_field",
        magicgui_factory=bad_container,
        pydantic_attr_factory=get_bad_value,
    )
    c = widgets.Container()
    tr.add_pydantic_to_container(Model, c)
    py_kwargs = {}
    tr.get_pydantic_kwargs(c, Model, py_kwargs)
    assert py_kwargs["bad_field"] == py_kwargs["bad_field"]


def test_yt_data_container():
    data_container = gu.get_yt_data_container()
    assert hasattr(data_container, "filename")
    assert hasattr(data_container.selections, "resolution")
