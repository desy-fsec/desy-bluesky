from typing import Optional
from pydantic import Field

from .nexusformat_models import (
    NXfieldModel,
    NXgroupModel,
    NXattrModel
)

class NXpositionerModel(NXgroupModel):
    default: Optional[NXattrModel] = Field(None, description="Default attribute")
    name: Optional[NXfieldModel] = Field(None, description="Name of the positioner")
    value: Optional[NXfieldModel] = Field(None, description="Current value of the positioner")
    raw_value: Optional[NXfieldModel] = Field(None, description="Raw value of the positioner")
    target_value: Optional[NXfieldModel] = Field(None, description="Target value of the positioner")
    tolerance: Optional[NXfieldModel] = Field(None, description="Tolerance of the positioner")
    soft_limit_min: Optional[NXfieldModel] = Field(None, description="Minimum soft limit of the positioner")
    soft_limit_max: Optional[NXfieldModel] = Field(None, description="Maximum soft limit of the positioner")
    velocity: Optional[NXfieldModel] = Field(None, description="Velocity of the positioner")
    acceleration_time: Optional[NXfieldModel] = Field(None, description="Acceleration time of the positioner")
    controller_record: Optional[NXfieldModel] = Field(None, description="Controller record of the positioner")
    depends_on: Optional[NXfieldModel] = Field(None, description="Dependency of the positioner")
    TRANSFORMATIONS: Optional[NXgroupModel] = Field(None, description="Transformations of the positioner")
    
    class Config:
        extra = 'forbid'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nxclass = "NXpositioner"
        if 'attrs' not in kwargs:
            self.attrs = {}
        if 'default' not in self.attrs:
            self.attrs['default'] = NXattrModel(value='value', dtype='char', shape=[])

    def __repr__(self):
        return f"NXPositionerModel(name={self.nxname}, class={self.nxclass})"

    def __str__(self):
        return f"NXPositionerModel(name={self.name}, attrs={self.attrs})"

    def __eq__(self, other):
        if not isinstance(other, NXpositionerModel):
            return False
        return self.name == other.name and self.attrs == other.attrs

    def __ne__(self, other):
        return not self.__eq__(other)