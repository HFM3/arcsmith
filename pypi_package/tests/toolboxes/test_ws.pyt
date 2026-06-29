# -*- coding: utf-8 -*-
"""
test_ws.pyt
ArcGIS Pro test toolbox for arcsmith.ws.

ws.py has no pytest coverage at all: both functions call into arcpy
(CreateFileGDB, Exists, Delete, env.scratchGDB) and cannot run off a machine.
This toolbox drives them so the behaviors can be verified live:

    - init_gdb     (folder creation, idempotent reuse, overwrite=fresh)
    - temp_space   ('memory' vs the on-disk scratch GDB)
"""

import sys
from pathlib import Path

# Make the in-repo src/ layout importable so this toolbox tests the actual
# source under ../../src, with no install required (mirrors tests/conftest.py).
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import arcpy
import arcsmith
from importlib import reload

# Reload arcsmith from ../../src on every toolbox load, so edits to the package
# source are picked up without restarting ArcGIS Pro (Pro caches imports for the
# session). Submodules reload before the package; flds before fc, since fc
# imports from flds.
for _name in ("param", "flds", "fc", "tbl", "ws", "lyr"):
    reload(getattr(arcsmith, _name))
reload(arcsmith)


# ===========================================================================
class Toolbox:
    def __init__(self):
        self.label = "Test arcsmith.ws"
        self.alias = "test_arcsmith_ws"
        self.tools = [
            InitGdb,
            TempSpace,
        ]


# ===========================================================================
# 1. init_gdb
# ===========================================================================
class InitGdb:
    def __init__(self):
        self.label = "01 Init GDB"
        self.description = (
            "Test arcsmith.ws.init_gdb - creates a file geodatabase, making the "
            "folder if needed. Run once to create it, then run again with "
            "Overwrite OFF to confirm the existing GDB is reused (idempotent) - "
            "watch for the 'already exists, reusing' message. Run with Overwrite "
            "ON to confirm it is deleted and recreated empty. A trailing '.gdb' "
            "in the name is stripped, so 'glacier' and 'glacier.gdb' behave "
            "identically."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Target Folder",
            name="folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Geodatabase Name (with or without .gdb)",
            name="gdb_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        p1.value = "arcsmith_test.gdb"

        p2 = arcpy.Parameter(
            displayName="Overwrite (delete and recreate if it exists)",
            name="overwrite",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p2.value = False

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        folder = parameters[0].valueAsText
        gdb_name = parameters[1].valueAsText
        overwrite = bool(parameters[2].value)

        out = arcsmith.ws.init_gdb(folder, gdb_name, overwrite=overwrite)
        arcpy.AddMessage(f"init_gdb returned -> {out}")
        arcpy.AddMessage(f"Exists now: {arcpy.Exists(out)}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 2. temp_space
# ===========================================================================
class TempSpace:
    def __init__(self):
        self.label = "02 Temp Space"
        self.description = (
            "Test arcsmith.ws.temp_space - returns a workspace for intermediate "
            "outputs. With 'Use memory' ON it returns the in-memory 'memory' "
            "workspace; OFF it returns the on-disk session scratch GDB "
            "(inspectable in the Catalog pane). The tool writes a tiny throwaway "
            "feature class into the returned workspace to prove it is writable."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Use Memory ('memory' vs scratch GDB)",
            name="use_memory",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p0.value = True

        return [p0]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        use_memory = bool(parameters[0].value)
        ws = arcsmith.ws.temp_space(use_memory=use_memory)
        arcpy.AddMessage(f"temp_space(use_memory={use_memory}) -> {ws}")

        # Prove the workspace is writable by creating and deleting a scratch FC.
        scratch = f"{ws}/arcsmith_temp_space_probe"
        if arcpy.Exists(scratch):
            arcpy.management.Delete(scratch)
        arcpy.management.CreateFeatureclass(ws, "arcsmith_temp_space_probe", "POINT")
        arcpy.AddMessage(f"Wrote probe FC -> {scratch}")
        arcpy.management.Delete(scratch)
        arcpy.AddMessage("Probe FC deleted; workspace confirmed writable.")

    def postExecute(self, parameters):
        return
