from pydantic import BaseModel, Field
from typing import List, Optional, Union

class Attribute(BaseModel):
    name: str
    value: Union[str, float, int]


class NXField(BaseModel):
    name: str
    type: str
    dtype: Optional[str] = None
    value: Optional[Union[str, float, int]] = None
    shape: Optional[List[int]] = None
    group: Optional[str] = None
    attrs: Optional[dict] = None
    kwargs: Optional[dict] = None
    attributes: Optional[List[Attribute]] = None


class NXGroup(BaseModel):
    NX_class: str
    name: str
    type: str
    fields: List[NXField]


class Definition(BaseModel):
    definition: NXGroup


# Example usage
example_definition = Definition(
    definition=NXGroup(
        NX_class="NXpositioner",
        name="positioner",
        type="group",
        fields=[
            NXField(
                name="default",
                type="NXfield",
                dtype="float64",
                value=None,
                shape=[],
                group="positioner",
                attrs={},
                kwargs={},
                attributes=[
                    Attribute(name="dtype", value="float64"),
                    Attribute(name="value", value="./value")
                ]
            ),
            NXField(
                name="name",
                type="NXfield",
                attributes=[
                    Attribute(name="dtype", value="char"),
                    Attribute(name="value", value="{NAME}")
                ]
            ),
            NXField(
                name="description",
                type="NXfield",
                attributes=[
                    Attribute(name="dtype", value="char"),
                    Attribute(name="value", value="0msVME58Motor")
                ]
            ),
            NXField(
                name="value",
                type="NXdata",
                attributes=[
                    Attribute(name="dtype", value="float64"),
                    Attribute(name="value", value="{VALUE}")
                ]
            )
        ]
    )
)