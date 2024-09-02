from typing import Optional, Any, Dict

from pydantic import ValidationError

from .nexusformat_models import (
    NXattrModel,
    NXfieldModel,
    NXgroupModel,
    NXlinkModel,
    NXobjectModel,
    NXdataModel,
    NXentryModel,    
)
from .NXpositioner import NXpositionerModel

__all__ = ["NXattrModel",
           "NXfieldModel",
           "NXgroupModel",
           "NXlinkModel",
           "NXobjectModel",
           "NXdataModel",
           "NXpositionerModel",
           'NXentryModel',]

def validate_nexus_tree(tree: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    def validate_object(obj: Dict[str, Any]):
        if 'nxclass' not in obj:
            return
        obj_class_name = obj['nxclass']
        model_name = obj_class_name + 'Model'
        if model_name not in globals():
            raise ValueError(f"Model '{model_name}' not found for class '{obj_class_name}'.")
        model = globals()[model_name]
        model(**obj)
        for nested_obj in obj.values():
            if isinstance(nested_obj, dict):
                validate_object(nested_obj)

    if 'nxclass' not in tree:
        raise ValueError("The root object must have a top level 'nxclass' attribute.")
    
    validate_object(tree)
    return tree
        
        