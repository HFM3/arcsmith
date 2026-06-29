<div class="as-hero" markdown>
<div class="as-hero__eyebrow">Getting started</div>
<h2 class="as-hero__title">Installation</h2>
<p class="as-hero__sub">ArcSmith requires <code>arcpy</code>, which ships with ArcGIS Pro and is not available outside its Python environment.</p>
</div>

!!! tip "Self-contained install  (recommended for portable tools)"
    Copy the `arcsmith` source folder into the same directory as the `.pyt` file. Python finds it locally and `import arcsmith` works as normal. The source folder can be downloaded from <a class="as-hero__link" href=https://arcsmith.dev/>ArcSmith.dev</a>.

    ```
    MyToolbox/
    ├── MyToolbox.pyt
    └── arcsmith/
    ```

??? note "Install into a cloned environment"
    ArcGIS Pro does not allow the default `arcgispro-py3` environment to be modified. Clone it first using the Python Package Manager.

    In ArcGIS Pro, open **Project > Python > Python Package Manager**. Select **Manage Environments**, then choose **Clone** next to `arcgispro-py3`. Give the clone a name and wait for it to complete. Once created, select it as the active environment and restart ArcGIS Pro.

    With the cloned environment active, open a terminal and install:

    ```
    py -m pip install arcsmith
    ```

??? note "Quick install: existing environment"
    If a suitable cloned environment is already active, install directly from a terminal:

    ```
    py -m pip install arcsmith
    ```

---

---
<br>

<div class="as-hero" markdown>
<div class="as-hero__eyebrow">ArcSmith is ready</div>
<h2 class="as-hero__title">Build an ArcSmith tool</h2>
<p class="as-hero__sub">The Quickstart walks you through a complete, runnable filter tool with a field picker, live dropdown, and SQL export in a few minutes.</p>
<ul class="as-hero__highlights">
<li>See what ArcSmith it its modules can do</li>
<li>Learn where each module plugs into the toolbox lifecycle</li>
<li>Build a complete, runnable filter tool with four parameters</li>
</ul>
<p class="as-hero__sub" style="margin-top:1.25rem;margin-bottom:0"><a class="as-hero__link" href="../quick_start">Quickstart &rarr;</a></p>
</div>

<br><br><br><br><br>