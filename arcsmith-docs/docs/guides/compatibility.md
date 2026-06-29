<div class="as-hero" markdown>
<div class="as-hero__eyebrow">Reference</div>
<h2 class="as-hero__title">Compatibility &amp; stability</h2>
<p class="as-hero__sub">Which ArcGIS Pro and Python versions ArcSmith supports, and what the version number promises about API stability.</p>
</div>

## Supported environments

ArcSmith requires `arcpy`, which ships only with ArcGIS Pro, and declares
`requires-python = ">=3.11"`. Any ArcGIS Pro release that bundles Python 3.11 or
newer is therefore supported. ArcGIS Pro first shipped Python 3.11 in **Pro
3.3**, which is the supported floor. `pip` refuses to install ArcSmith into an
older environment.

| ArcGIS Pro | Bundled Python | Supported |
|---|---|---|
| 3.3 | 3.11 | ✅ (floor) |
| 3.4 | 3.11 | ✅ |
| 3.5 | 3.11 | ✅ |
| 3.6 | 3.13 | ✅ |
| 3.7 | 3.13 | ✅ |
| ≤ 3.2 | 3.9 | ❌ below floor |

Each Pro release advances the Python patch version, and the minor version steps
up roughly every third release (3.9 through Pro 3.2, 3.11 from Pro 3.3, 3.13 from
Pro 3.6). The exact patch level for a release is listed in that release's ArcGIS
Pro release notes. ArcSmith does not pin a patch version. It targets the 3.11+
language and standard library only, so a newer Pro release is supported as long
as its bundled Python is 3.11 or later.

---

## Versioning policy

ArcSmith follows [Semantic Versioning](https://semver.org/) **from 1.0.0 onward**:

- **MAJOR**: incompatible public API changes.
- **MINOR**: backwards-compatible additions.
- **PATCH**: backwards-compatible fixes.

!!! warning "Pre-1.0"
    While the version is `0.x`, the public API is still settling and breaking
    changes can land in any release. The changelog shipped with the package
    records the renames and behavior changes made so far. 1.0 is the point at
    which this surface freezes.

---

## Public vs. private API

The public API is everything **not** prefixed with an underscore. A name like
`lyr._seed_styles` or `param._broadcast` is an internal helper. It can change or
disappear in any release, including patch releases, and should not be relied on.
The internal `arcsmith._types` module is private for the same reason.

Each module's `__all__` lists its public functions, and the per-module
[reference sheets](../index.md) document the same set.

`lyr.PRESETS`, the registered style-preset dictionary, is part of the public
surface. You can read it and pass its names to `lyr.simple_sym` and `lyr.add`.
The catalogue grows over time, so new preset names may be added in a minor
release, but an existing preset name will not be removed or repurposed without
going through the deprecation process below.

---

## Deprecation policy

From 1.0 onward, a public function, parameter, or preset will not be removed
without warning. It is first deprecated for at least one minor release: it keeps
working, its planned removal is announced in the changelog, and (where practical)
a runtime warning is raised when it is used. Removal happens no earlier than the
following minor release, which gives a toolbox a full release cycle to migrate.

Before 1.0 this cushion does not apply. As noted above, breaking changes can land
in any `0.x` release, and the changelog is the record of what changed.

---

## Reporting a compatibility issue

Please open an issue on the [issue tracker](https://github.com/HFM3/arcsmith/issues).
To make it reproducible, include:

- the ArcSmith version (`pip show arcsmith`),
- the ArcGIS Pro version and its bundled Python version (Pro **Settings > About**, or run `import sys; print(sys.version)` in the Python window),
- the full `arcpy` error message and traceback, and
- a minimal snippet or `.pyt` excerpt that triggers the problem.