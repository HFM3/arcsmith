"""Shared test setup.

``arcpy`` cannot be imported off an ArcGIS Pro machine, and every arcsmith
module does ``import arcpy`` at the top. These tests therefore cover only the
*pure* helpers — functions whose logic never calls into arcpy at runtime
(string/SQL building, color parsing, list broadcasting, field-set resolution,
parameter-state inspection). To let those modules import at all, a minimal stub
``arcpy`` is injected into ``sys.modules`` before arcsmith is imported, and the
``src`` layout is placed on the path so the package is importable without an
install.

Anything that actually drives arcpy (cursors, Describe, geoprocessing tools) is
out of scope here and belongs in on-machine integration tests.
"""

import sys
import types
from pathlib import Path

# Make the src-layout package importable without installation.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Inject a bare stub so ``import arcpy`` succeeds at module import time. The
# pure helpers under test never touch its attributes; if a test ever calls a
# function that does, it will fail loudly with AttributeError rather than
# silently passing.
if "arcpy" not in sys.modules:
    sys.modules["arcpy"] = types.ModuleType("arcpy")