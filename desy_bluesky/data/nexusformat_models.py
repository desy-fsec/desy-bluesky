from pydantic import BaseModel, Field, model_validator, ValidationError
from typing import Optional, Union, Dict, Any, List, Tuple
import numpy.typing as npt
import numpy as np

__all__ = ['NXattrModel',
           'NXfieldModel',
           'NXgroupModel',
           'NXobjectModel',
           'NXlinkModel',
           'NXlinkFieldModel',
           'NXlinkGroupModel',
           'NXdataModel',
           'NXentryModel',]

# scalar type
Scalar = Union[str, float, int]
# array-like i.e. list, tuple, numpy.ndarray
ArrayLike = npt.ArrayLike
# numpy datatype
NPType = np.dtype
# numpy array
NPArray = npt.NDArray

class NXattrModel(BaseModel):
    value: Union[str, Scalar, ArrayLike] = Field(..., description="Value of the attribute.")
    dtype: Optional[str] = Field(None, description="Data type of the attribute.")
    shape: Optional[Union[list, Tuple[int]]] = Field(None, description="Shape of the attribute.")
    
    @model_validator(mode='before')
    def remove_nxclass(cls, values):
        values.pop('nxclass', None)
        return values
    
    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'
    
class NXFileModel(BaseModel):
    name: str = Field(..., description="Name of the HDF5 file.")
    mode: str = Field('r', description="Read/write mode of the HDF5 file.")
    recursive: Optional[bool] = Field(None, description="If True, the file tree is loaded recursively.")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Keyword arguments for opening the h5py File object.")

    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'

class NXobjectModel(BaseModel):
    nxclass: Optional[str] = Field(None, description="The class of the NXobject.")
    nxname: Optional[str] = Field(None, description="The name of the NXobject.")
    nxgroup: Optional['NXgroupModel'] = Field(None, description="The parent group containing this object within a NeXus tree.")
    nxpath: Optional[str] = Field(None, description="The path to this object with respect to the root of the NeXus tree.")
    nxroot: Optional['NXgroupModel'] = Field(None, description="The root object of the NeXus tree containing this object.")
    nxfile: Optional['NXFileModel'] = Field(None, description="The file handle of the root object of the NeXus tree containing this object.")
    nxfilename: Optional[str] = Field(None, description="The file name of NeXus object's tree file handle.")
    attrs: Dict[str, Any] = Field(default_factory=dict, description="A dictionary of the NeXus object's attributes.")

    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'

class NXfieldModel(NXobjectModel):
    value: Optional[Union[int, float, ArrayLike, str]] = Field(..., description="Value of the field.")
    name: Optional[str] = Field(None, description="Name of the field.")
    shape: Optional[Union[list, Tuple[int]]] = Field(None, description="Shape of the field.")
    dtype: Optional[Union[str, np.dtype]] = Field(None, description="Data type of the field.")
    group: Optional['NXgroupModel'] = Field(None, description="The parent group containing this field within a NeXus tree.")
    attrs: Optional[Dict[str, 'NXattrModel']] = Field(default_factory=dict, description="A dictionary of the NeXus field's attributes.")
    
    @model_validator(mode='before')
    def remove_nxclass(cls, values):
        values.pop('nxclass', None)
        return values
    
    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'

class NXgroupModel(NXobjectModel):
    def __init__(self, **data: Any):
        super().__init__(**data)
        # Perform validation
        accepted_types = (NXfieldModel, NXgroupModel, NXattrModel)
        errors = []
        for key, value in data.items():
            if key not in self.model_fields and not isinstance(value, accepted_types):
                errors.append(ValidationError([{'loc': key, 'msg': f"Invalid type '{type(value)}' for key '{key}'.", 'type': 'type_error'}], self.__class__))
        if errors:
            raise ValidationError(errors, self.__class__)

    @property
    def nxclass(self) -> str:
        return "NXgroup"

    class Config:
        arbitrary_types_allowed = True
        extra = 'allow'  # Allow extra fields

class NXlinkModel(NXobjectModel):
    target: Optional[str] = Field(None, description="The target of the link.")
    file: Optional[str] = Field(None, description="The file containing the target of the link.")
    name: Optional[str] = Field(None, description="The name of the link.")
    group: Optional['NXgroupModel'] = Field(None, description="The parent group containing this link within a NeXus tree.")
    abspath: Optional[str] = Field(None, description="The absolute path to the target of the link.")
    soft: Optional[bool] = Field(None, description="If True, the link is a soft link.")
    
    class Config:
        extra = 'forbid'

class NXlinkFieldModel(NXlinkModel):
    @property
    def nxdata(self) -> Optional[Union[int, float, str, list, tuple]]:
        return self.target.value if isinstance(self.target, NXfieldModel) else None

class NXlinkGroupModel(NXlinkModel):
    @property
    def entries(self) -> Optional[Dict[str, Union[NXfieldModel, NXgroupModel]]]:
        return self.target.entries if isinstance(self.target, NXgroupModel) else None

class NXdataModel(NXgroupModel):
    signal: Optional[NXfieldModel] = Field(None, description="Field defining the data to be plotted")
    axes: Optional[Tuple[NXfieldModel, ...]] = Field(None, description="Tuple of one-dimensional fields defining the plot axes")
    errors: Optional[NXfieldModel] = Field(None, description="Field containing the standard deviations of the signal values")
    weights: Optional[NXfieldModel] = Field(None, description="Field containing signal value weights")
    
    class Config:
        extra = 'forbid'

class NXentryModel(NXgroupModel):
    @property
    def nxclass(self) -> str:
        return "NXentry"

    def __add__(self, other: 'NXentryModel') -> 'NXentryModel':
        # Implement the addition logic here
        pass

    def __sub__(self, other: 'NXentryModel') -> 'NXentryModel':
        # Implement the subtraction logic here
        pass

    def set_default(self, over: bool = False):
        # Implement the set_default logic here
        pass

    @property
    def plottable_data(self):
        # Implement the plottable_data logic here
        pass

    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'
    