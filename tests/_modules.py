"""Helper for importing the numbered pipeline scripts under scripts/ as modules.

Their filenames start with digits (1_preprocess.py, 2_variant_calling.py, ...)
to make the pipeline order obvious, which means they can't be imported with a
plain `import` statement (not a valid Python identifier). Load them by file
path instead.
"""
import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def load_script_module(filename):
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
