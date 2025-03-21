from pydantic import BaseModel
from typing import Dict, Any

from nexusformat.nexus.tree import NXfield, NXattr, NXgroup


class NexusWriter:
    _model: BaseModel
    _file_path: str
    _tree: Any

    def __init__(self, model: BaseModel, file_path: str = ""):
        if not issubclass(model.__class__, BaseModel):
            raise TypeError("data must be an instance of a validated pydantic model")
        self._model = model
        self._file_path = file_path

    @property
    def model(self):
        return self._model

    @property
    def file_path(self):
        return self._file_path

    @property
    def tree(self):
        return self._tree

    def write(self):
        """
        1. Dump the model to an object called tree
        2. If the value in a tree is a dict, it is another Nexus object with
           its class encoded by the nxclass key.
        3. Keys with non-dict entries are parameters of the Nexus object.
        4. If the value is None, skip the key.
        5. Recursively traverse the tree and instantiate Nexus objects,
           adding them as children to their parent objects.
        """
        tree = self._model.model_dump()
        obj = self._instantiate_nexus_object(tree)
        self._tree = obj

    def _instantiate_nexus_object(self, tree: Dict[str, Any]):
        nxclass = tree.pop("nxclass")
        children = {}

        for key, value in tree.items():
            if value is None:
                continue
            child_class_name = value.pop("nxclass")
            child_class = globals().get(child_class_name)

            if child_class in {NXfield, NXattr, NXgroup}:
                children[key] = (
                    self._instantiate_nexus_field(value)
                    if child_class is NXfield
                    else child_class(**value)
                )
            elif issubclass(child_class, NXgroup):
                value["nxclass"] = child_class_name
                children[key] = self._instantiate_nexus_object(value)

        obj_class = globals().get(nxclass)
        return obj_class(**children)

    def _instantiate_nexus_field(self, obj: Dict[str, Any]):
        for key, value in obj.items():
            if value is None:
                continue
            if isinstance(value, dict) and "nxclass" in value:
                _ = value.pop("nxclass")
                obj[key] = NXattr(**value)
        return NXfield(**obj)
