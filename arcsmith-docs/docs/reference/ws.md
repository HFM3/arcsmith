<div class="as-hero" markdown>
<div class="as-hero__eyebrow">arcsmith.ws</div>
<h2 class="as-hero__title">Workspace</h2>
<p class="as-hero__sub">Helpers for setting up geodatabase workspaces inside 'Tool.execute'.</p>
<ul class="as-hero__highlights">
<li>Create a file geodatabase with automatic parent folder creation</li>
<li>Get a workspace path for intermediate outputs, switching between memory and a scratch <code>.gdb</code></li>
</ul>
</div>

## Functions of the `ws` module

## init_gdb

Creates a file geodatabase at the specified location, creating the parent folder if it does not already exist. If the geodatabase already exists, it is reused by default, or recreated when `overwrite=True`.

```python
init_gdb(folder, gdb_name, overwrite=False) -> str
```

| Parameter  | Type            | Default  | Description                                             |
|------------|-----------------|----------|---------------------------------------------------------|
| `folder`   | `str` or `Path` | required | Folder in which to create the geodatabase.              |
| `gdb_name` | `str`           | required | Name of the geodatabase. A trailing `.gdb` extension, if supplied, is stripped, so `"glacier"` and `"glacier.gdb"` behave identically. |
| `overwrite`| `bool`          | `False`  | What to do when the target `.gdb` already exists. `False` (default) reuses the existing geodatabase and returns its path (idempotent). `True` deletes and recreates it empty. |

!!! success "Returns"
    `str`: absolute path to the geodatabase. This is the newly created `.gdb` unless an existing one was reused (`overwrite=False`).

!!! note "Existing geodatabases"
    `arcpy.env.overwriteOutput` does not apply to geodatabase creation, so `CreateFileGDB` raises if the `.gdb` already exists. `init_gdb` handles this automatically: by default it reuses the existing workspace, and `overwrite=True` forces a fresh, empty one. Reuse hands back whatever schema is already on disk, so pass `overwrite=True` if a clean workspace matters.

**Examples**

```python
# Create a geodatabase
gdb = arcsmith.ws.init_gdb(r"C:/Projects/Glacier", "glacier")
# C:/Projects/Glacier/glacier.gdb

# Create and set as the arcpy workspace in one line
arcpy.env.workspace = arcsmith.ws.init_gdb(folder, gdb_name)

# Force a fresh, empty geodatabase even if one already exists
gdb = arcsmith.ws.init_gdb(folder, "glacier", overwrite=True)
```

---

## temp_space

Returns a workspace path for intermediate outputs, either the in-memory workspace or the session scratch geodatabase.

```python
temp_space(use_memory=True) -> str
```

| Parameter    | Type   | Default | Description                                                                                          |
|--------------|--------|---------|------------------------------------------------------------------------------------------------------|
| `use_memory` | `bool` | `True`  | If `True`, returns `'memory'`. If `False`, returns `arcpy.env.scratchGDB` for on-disk inspection.   |

!!! success "Returns"
    `str`: `'memory'` or the absolute path to the scratch geodatabase.

!!! tip "Development workflow"
    Set `use_memory=False` while building a tool to inspect intermediate outputs in ArcGIS Pro. Switch back to `True` (the default) for production runs; no other code changes needed.

!!! note "`memory` limitations"
    The `'memory'` workspace does not support everything an on-disk geodatabase does. Certain field types, attribute indexes, and a handful of tools cannot write to it. If a tool fails against `'memory'`, use `use_memory=False` for compatibility, not only for inspection.

**Examples**

```python
# Production: intermediates go to memory (default)
ws = arcsmith.ws.temp_space()
tmp = f"{ws}/trails_temp"
# tmp = "memory/trails_temp"

# Development: intermediates written to scratch GDB for inspection
ws = arcsmith.ws.temp_space(use_memory=False)
tmp = f"{ws}/trails_temp"
# tmp = "C:/Users/.../scratch.gdb/trails_temp"
```

<br><br><br><br><br>