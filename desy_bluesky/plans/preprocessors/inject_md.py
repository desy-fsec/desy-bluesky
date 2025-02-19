from typing import Dict
from bluesky.preprocessors import inject_md_decorator


class InjectMD:
    def __init__(self, meta: Dict = None):
        self.md = meta or {}

    def set_metadata(self, meta):
        self.md = meta

    def add_metadata(self, meta):
        self.md.update(meta)

    def __call__(self, plan):
        @inject_md_decorator(self.md)
        def inner():
            yield from plan

        return inner()
