import nxarray

from bluesky.callbacks.broker import BrokerCallbackBase


class RunAddedCallback(BrokerCallbackBase):
    """
    Very simple callback that saves each run to a CSV and HDF5 file.
    Requires nxarray to be installed.
    """
    def __init__(self, catalog, fields=None):
        if fields is None:
            fields = []
        super().__init__(fields)
        self.catalog = catalog

    def stop(self, doc):
        run_id = doc['run_start']
        run = self.catalog[run_id]
        xarr = run.xarray()
        xarr.to_dataframe().to_csv(f'run_{run_id}.csv')
        xarr.nxr.save(f'run_{run_id}.nx')