from pydantic import BaseModel


class NexusWriter:
    _models: list = []

    def __init__(self, model: BaseModel):
        if not issubclass(model.__class__, BaseModel):
            raise TypeError("data must be an instance of a validated pydantic model")
        self._models.append(model)

    @property
    def models(self):
        return self._models

    def write(self, model: BaseModel):
        pass
