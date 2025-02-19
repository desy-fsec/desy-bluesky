import yaml
from bluesky.run_engine import RunEngine


def run_user_sequence(path: str, run_engine: RunEngine):

    plans = []
    with open(path, "r") as f:
        try:
            sequence = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Error loading sequence file {path}. {e}")

    for plan_name in sequence:
        args = sequence[plan_name].get("args", [])
        kwargs = sequence[plan_name].get("kwargs", {})
        metadata = sequence[plan_name].get("metadata", {})

        for arg in args:
            if isinstance(arg, str):
                if arg in globals():
                    args[args.index(arg)] = globals()[arg]
            elif isinstance(arg, list):
                for item in arg:
                    if item in globals():
                        arg[arg.index(item)] = globals()[item]
        for key in kwargs:
            if isinstance(kwargs[key], str):
                if kwargs[key] in globals():
                    kwargs[key] = globals()[kwargs[key]]
            elif isinstance(kwargs[key], list):
                for item in kwargs[key]:
                    if item in globals():
                        kwargs[key][kwargs[key].index(item)] = globals()[item]

        plan = globals()[plan_name](*args, **kwargs)

        plans.append((plan, metadata))

    for plan, metadata in plans:
        run_engine(plan, metadata=metadata)
