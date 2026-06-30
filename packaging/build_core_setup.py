"""Compile the proprietary core (voiceclaw/core) to binary .pyd so shipped
builds keep FULL functionality while the core SOURCE stays unreadable.

Build machine only. Requires:  pip install cython  +  a C compiler
(Windows: "Microsoft C++ Build Tools").

    python packaging/build_core_setup.py build_ext --inplace

Produces voiceclaw/core/*.pyd beside the .py. Before packaging the installer,
delete the .py so ONLY the .pyd ships (see docs/OPEN_CORE.md).
"""
import sys
from setuptools import setup

try:
    from Cython.Build import cythonize
except ImportError:
    sys.exit("Cython not installed.  Run:  pip install cython")

MODULES = [
    "voiceclaw/core/local_skills.py",
    "voiceclaw/core/learned_skills.py",
]

setup(name="voiceclaw-core",
      ext_modules=cythonize(MODULES, language_level=3))
