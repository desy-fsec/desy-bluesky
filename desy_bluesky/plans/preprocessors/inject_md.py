from bluesky.preprocessors import inject_md_decorator

class InjectMD:
    def __init__(self, meta):
        self.md = meta

    def __call__(self, plan):
        @inject_md_decorator(self.md)
        def inner():
            yield from plan
        return inner()