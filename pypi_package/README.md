<p align="center">
  <img src="https://arcsmith.dev/docs/images/social-card.png" alt="ArcSmith - For tool builders. Shape rough scripts into polished .pyt tools." width="760">
</p>

# ArcSmith

> A tool builder's toolbox.

[![Python](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/arcsmith.svg)](https://pypi.org/project/arcsmith/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/HFM3/arcsmith/blob/HEAD/pypi_package/LICENSE)

### Shape rough scripts into polished .pyt tools.

ArcSmith is a Python library for GIS researchers. It does not replace `arcpy`; it works on top of it, handling common **Python toolbox** (`.pyt`) tasks such as reading parameter state, building quoted SQL `WHERE` clauses, applying symbology, populating value lists, and creating output geodatabases.

Full documentation at [ArcSmith.dev](https://arcsmith.dev)

---

## Installation

```bash
pip install arcsmith
```

Requires `arcpy`. Install into the ArcGIS Pro Python environment.

---

## Modules

| Module | Description |
|---|---|
| `arcsmith.param` | Parameter state detection, cascade resets, dropdown population, checkbox-driven visibility, and timely self-clearing validation messages |
| `arcsmith.lyr` | Add layers to a map, apply `.lyrx` or simple symbology, create group layers, retrieve or remove layers by name or source |
| `arcsmith.ws` | Create output geodatabases and route intermediate outputs to memory or scratch GDB |
| `arcsmith.fc` | Build SQL WHERE clauses, export filtered subsets, validate geometry types, compute polygon area |
| `arcsmith.flds` | Build field mappings, add/rename/delete fields, standardize blanks, list columns and unique values |
| `arcsmith.tbl` | Create standalone tables from rows, append rows, key/value field lookups, join external columns, manage tables in a map |

---

## Citing ArcSmith

Using ArcSmith in research or published work? A citation is appreciated (it is not
required under the MIT license, but documented use builds trust in the tool).
APA, Chicago, and BibTeX formats, kept current with each release, are at
**[arcsmith.dev/docs/cite](https://arcsmith.dev/docs/cite/)**.

```bibtex
@software{ArcSmith,
  author  = {Mros, III, Henry F.},
  title   = {ArcSmith: ArcPy Toolbox Utilities},
  year    = {2026},
  version = {0.0.7},
  url     = {https://pypi.org/project/arcsmith/}
}
```

---

## License

[MIT](https://github.com/HFM3/arcsmith/blob/HEAD/pypi_package/LICENSE). Free to use, modify, and redistribute, including in commercial or proprietary tools, as long as the copyright notice and license text are retained. See the LICENSE file for the full terms.