from typing import Optional, Union, dict, list, any

from nexusformat.nexus.tree import NXgroup, NXfield, NXattr, NXlink, NXentry, NXdata, NXroot
from desy_bluesky.data.nexusformat_models import *

def get_nxgroup(grp: Optional[NXgroupModel] = None) -> NXgroup:
    for obj_name, obj in grp.items():
        pass