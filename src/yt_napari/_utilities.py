import importlib


def dependency_is_missing(dep: str) -> bool:
    # check if a dependency is missing
    try:
        _ = importlib.import_module(dep)
        is_missing = False
    except ModuleNotFoundError:
        is_missing = True
    return is_missing
