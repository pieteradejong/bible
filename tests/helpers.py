"""Import builders from scripts/ without turning the repo into a package.

The builders are top-level scripts, not a library, and they read
data/curated/books.json at import time -- so tests must run from the repo root.
They do *not* touch data/raw/, which is why the fast suite works offline.
"""
import importlib.util, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
_cache = {}


def builder(name):
    """Import scripts/<name>.py once and hand back the module."""
    if name in _cache:
        return _cache[name]
    path = ROOT / "scripts" / f"{name}.py"
    if not path.exists():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(f"_b_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _cache[name] = mod
    return mod
