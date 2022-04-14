import pydantic
import pytest
from magicgui import type_map, widgets

from yt_napari import _gui_utilities as gu


def test_set_default():
    assert gu.set_default(1, None) == 1
    assert gu.set_default(None, 1) == 1


def test_registry():
    reg = gu.MagicPydanticRegistry()

    class Model(pydantic.BaseModel):
        field_1: int = 1

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

    func, args, kwargs = reg.registry[Model]["field_1"]["pydantic"]
    pyvalue = reg.get_pydantic_attr(Model, "field_1", widget_instance)
    assert pyvalue == "2_testxyz"
