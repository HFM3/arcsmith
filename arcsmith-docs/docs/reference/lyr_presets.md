<div class="as-hero" markdown>
<div class="as-hero__eyebrow">arcsmith.lyr</div>
<h2 class="as-hero__title">Style presets</h2>
<p class="as-hero__sub">Named symbology bundles for <code>simple_sym</code>. Each preset sets a fill, stroke, and width suited to a geometry type.</p>
</div>

These are the registered values of `arcsmith.lyr.PRESETS`. Pass any name below as the `preset` argument to [`simple_sym`](lyr.md#simple_sym), for example `arcsmith.lyr.simple_sym(lyr, preset="simple_blue")`. Explicit style arguments override a preset, and a one-off style `dict` can be passed in place of a name. See the [Presets section](lyr.md#presets) of `simple_sym` for the full resolution order and the geometry matching rules.

!!! note "Geometry is advisory by default"
    The **Geometry** column below records the shape each preset was *designed* for, not a restriction. By default `simple_sym` applies any preset to any geometry, mapping its properties onto whatever the target supports: a Polygon fills and outlines, a Point styles its marker body and outline, and a Polyline takes the stroke as its line and drops the fill. Pass `simple_sym(..., strict_geom=True)` to enforce the listed geometry instead. See the [geometry table](lyr.md#simple_sym) for exactly which properties take effect per geometry.

---

## Simple color fills

A pale tint fill with a deep, saturated same-hue outline. These are designed for Polygon, Point, and Multipoint layers (which carry a fill), but apply to any geometry by default. On a Polyline the fill is dropped and the outline color becomes the line. Intended for quick, attractive output.

Each simple fill hue also has a point companion (`simple_pt_*`) and a line companion (`simple_ln_*`), listed below the fills. They share the saturated edge color of the matching fill, so a polygon, a point, and a line of the same hue read as a set. This is what lets `add` give each geometry a distinct default. A polygon gets the pale fill, a point gets a solid marker, and a line gets a colored stroke, so the three do not blend together on the same map.

| Preset | Symbol                                                                                      | Fill | Stroke | Width |
|--------|---------------------------------------------------------------------------------------------|------|--------|-------|
| `simple_red` | <span class="as-sym as-sym--poly" style="--fill:#FFBEBE;--stroke:#A80000;--w:2.2px"></span> | <span class="as-swatch" style="background:#FFBEBE"></span> `#FFBEBE` | <span class="as-swatch" style="background:#A80000"></span> `#A80000` | 0.70  |
| `simple_orange` | <span class="as-sym as-sym--poly" style="--fill:#FFEBAF;--stroke:#A83800;--w:2.2px"></span> | <span class="as-swatch" style="background:#FFEBAF"></span> `#FFEBAF` | <span class="as-swatch" style="background:#A83800"></span> `#A83800` | 0.70  |
| `simple_yellow` | <span class="as-sym as-sym--poly" style="--fill:#FFFFBE;--stroke:#A87000;--w:2.2px"></span> | <span class="as-swatch" style="background:#FFFFBE"></span> `#FFFFBE` | <span class="as-swatch" style="background:#A87000"></span> `#A87000` | 0.70  |
| `simple_lime` | <span class="as-sym as-sym--poly" style="--fill:#ECFFBE;--stroke:#4C7300;--w:2.2px"></span> | <span class="as-swatch" style="background:#ECFFBE"></span> `#ECFFBE` | <span class="as-swatch" style="background:#4C7300"></span> `#4C7300` | 0.70  |
| `simple_green` | <span class="as-sym as-sym--poly" style="--fill:#D3FFBE;--stroke:#267300;--w:2.2px"></span> | <span class="as-swatch" style="background:#D3FFBE"></span> `#D3FFBE` | <span class="as-swatch" style="background:#267300"></span> `#267300` | 0.70  |
| `simple_teal` | <span class="as-sym as-sym--poly" style="--fill:#BEFFE8;--stroke:#00734C;--w:2.2px"></span> | <span class="as-swatch" style="background:#BEFFE8"></span> `#BEFFE8` | <span class="as-swatch" style="background:#00734C"></span> `#00734C` | 0.70  |
| `simple_sky` | <span class="as-sym as-sym--poly" style="--fill:#BEF7FF;--stroke:#005C73;--w:2.2px"></span> | <span class="as-swatch" style="background:#BEF7FF"></span> `#BEF7FF` | <span class="as-swatch" style="background:#005C73"></span> `#005C73` | 0.70  |
| `simple_blue` | <span class="as-sym as-sym--poly" style="--fill:#BEE8FF;--stroke:#004C73;--w:2.2px"></span> | <span class="as-swatch" style="background:#BEE8FF"></span> `#BEE8FF` | <span class="as-swatch" style="background:#004C73"></span> `#004C73` | 0.70  |
| `simple_indigo` | <span class="as-sym as-sym--poly" style="--fill:#C9BEFF;--stroke:#1C3C73;--w:2.2px"></span> | <span class="as-swatch" style="background:#C9BEFF"></span> `#C9BEFF` | <span class="as-swatch" style="background:#1C3C73"></span> `#1C3C73` | 0.70  |
| `simple_purple` | <span class="as-sym as-sym--poly" style="--fill:#E8BEFF;--stroke:#4C0073;--w:2.2px"></span> | <span class="as-swatch" style="background:#E8BEFF"></span> `#E8BEFF` | <span class="as-swatch" style="background:#4C0073"></span> `#4C0073` | 0.70  |
| `simple_pink` | <span class="as-sym as-sym--poly" style="--fill:#FFBEE8;--stroke:#A80084;--w:2.2px"></span> | <span class="as-swatch" style="background:#FFBEE8"></span> `#FFBEE8` | <span class="as-swatch" style="background:#A80084"></span> `#A80084` | 0.70  |
| `simple_brown` | <span class="as-sym as-sym--poly" style="--fill:#E8D3BE;--stroke:#734C00;--w:2.2px"></span> | <span class="as-swatch" style="background:#E8D3BE"></span> `#E8D3BE` | <span class="as-swatch" style="background:#734C00"></span> `#734C00` | 0.70  |
| `simple_grey` | <span class="as-sym as-sym--poly" style="--fill:#E1E1E1;--stroke:#4E4E4E;--w:2.2px"></span> | <span class="as-swatch" style="background:#E1E1E1"></span> `#E1E1E1` | <span class="as-swatch" style="background:#4E4E4E"></span> `#4E4E4E` | 0.70  |
| `simple_slate` | <span class="as-sym as-sym--poly" style="--fill:#D6DCE4;--stroke:#4C5A66;--w:2.2px"></span> | <span class="as-swatch" style="background:#D6DCE4"></span> `#D6DCE4` | <span class="as-swatch" style="background:#4C5A66"></span> `#4C5A66` | 0.70  |

### Simple point markers

A solid same-hue marker with a grey outline, one per simple fill hue. The
marker body uses the saturated edge color of the matching simple fill, so
it is the slightly dark version of the hue. A default-styled point reads as
a distinct marker against the pale `simple_*` polygon fills instead of
blending into them. These match both Point and Multipoint layers, and `add`
applies one automatically when the new layer is a point.

| Preset | Symbol | Fill | Stroke | Width |
|--------|--------|------|--------|-------|
| `simple_pt_red` | <span class="as-sym as-sym--point" style="--fill:#A80000;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#A80000"></span> `#A80000` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_orange` | <span class="as-sym as-sym--point" style="--fill:#A83800;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#A83800"></span> `#A83800` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_yellow` | <span class="as-sym as-sym--point" style="--fill:#A87000;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#A87000"></span> `#A87000` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_lime` | <span class="as-sym as-sym--point" style="--fill:#4C7300;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#4C7300"></span> `#4C7300` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_green` | <span class="as-sym as-sym--point" style="--fill:#267300;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#267300"></span> `#267300` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_teal` | <span class="as-sym as-sym--point" style="--fill:#00734C;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#00734C"></span> `#00734C` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_sky` | <span class="as-sym as-sym--point" style="--fill:#005C73;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#005C73"></span> `#005C73` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_blue` | <span class="as-sym as-sym--point" style="--fill:#004C73;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#004C73"></span> `#004C73` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_indigo` | <span class="as-sym as-sym--point" style="--fill:#1C3C73;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#1C3C73"></span> `#1C3C73` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_purple` | <span class="as-sym as-sym--point" style="--fill:#4C0073;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#4C0073"></span> `#4C0073` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_pink` | <span class="as-sym as-sym--point" style="--fill:#A80084;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#A80084"></span> `#A80084` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_brown` | <span class="as-sym as-sym--point" style="--fill:#734C00;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#734C00"></span> `#734C00` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_grey` | <span class="as-sym as-sym--point" style="--fill:#4E4E4E;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#4E4E4E"></span> `#4E4E4E` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `simple_pt_slate` | <span class="as-sym as-sym--point" style="--fill:#4C5A66;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#4C5A66"></span> `#4C5A66` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |

### Simple lines

A solid same-hue stroke at a line weight, one per simple fill hue, again
using the saturated edge color of the matching simple fill. A simple line
and a simple point marker of the same hue therefore share a color and read
as siblings. The width sits above the polygon outline weight so a
default-styled line reads as a line rather than as a stray polygon outline.
`add` applies one automatically when the new layer is a polyline.

| Preset | Symbol | Stroke | Width |
|--------|--------|--------|-------|
| `simple_ln_red` | <span class="as-sym as-sym--line" style="--stroke:#A80000;--w:2px"></span> | <span class="as-swatch" style="background:#A80000"></span> `#A80000` | 1.50  |
| `simple_ln_orange` | <span class="as-sym as-sym--line" style="--stroke:#A83800;--w:2px"></span> | <span class="as-swatch" style="background:#A83800"></span> `#A83800` | 1.50  |
| `simple_ln_yellow` | <span class="as-sym as-sym--line" style="--stroke:#A87000;--w:2px"></span> | <span class="as-swatch" style="background:#A87000"></span> `#A87000` | 1.50  |
| `simple_ln_lime` | <span class="as-sym as-sym--line" style="--stroke:#4C7300;--w:2px"></span> | <span class="as-swatch" style="background:#4C7300"></span> `#4C7300` | 1.50  |
| `simple_ln_green` | <span class="as-sym as-sym--line" style="--stroke:#267300;--w:2px"></span> | <span class="as-swatch" style="background:#267300"></span> `#267300` | 1.50  |
| `simple_ln_teal` | <span class="as-sym as-sym--line" style="--stroke:#00734C;--w:2px"></span> | <span class="as-swatch" style="background:#00734C"></span> `#00734C` | 1.50  |
| `simple_ln_sky` | <span class="as-sym as-sym--line" style="--stroke:#005C73;--w:2px"></span> | <span class="as-swatch" style="background:#005C73"></span> `#005C73` | 1.50  |
| `simple_ln_blue` | <span class="as-sym as-sym--line" style="--stroke:#004C73;--w:2px"></span> | <span class="as-swatch" style="background:#004C73"></span> `#004C73` | 1.50  |
| `simple_ln_indigo` | <span class="as-sym as-sym--line" style="--stroke:#1C3C73;--w:2px"></span> | <span class="as-swatch" style="background:#1C3C73"></span> `#1C3C73` | 1.50  |
| `simple_ln_purple` | <span class="as-sym as-sym--line" style="--stroke:#4C0073;--w:2px"></span> | <span class="as-swatch" style="background:#4C0073"></span> `#4C0073` | 1.50  |
| `simple_ln_pink` | <span class="as-sym as-sym--line" style="--stroke:#A80084;--w:2px"></span> | <span class="as-swatch" style="background:#A80084"></span> `#A80084` | 1.50  |
| `simple_ln_brown` | <span class="as-sym as-sym--line" style="--stroke:#734C00;--w:2px"></span> | <span class="as-swatch" style="background:#734C00"></span> `#734C00` | 1.50  |
| `simple_ln_grey` | <span class="as-sym as-sym--line" style="--stroke:#4E4E4E;--w:2px"></span> | <span class="as-swatch" style="background:#4E4E4E"></span> `#4E4E4E` | 1.50  |
| `simple_ln_slate` | <span class="as-sym as-sym--line" style="--stroke:#4C5A66;--w:2px"></span> | <span class="as-swatch" style="background:#4C5A66"></span> `#4C5A66` | 1.50  |

---

## Feature presets

Cartographic presets named for the feature they represent. Most Polygon presets carry a fill and an outline. The `admin` presets are hollow, carrying only an outline so the area underneath stays visible. Polyline presets carry a line color only, and Point presets carry a marker fill with a grey outline. Point presets match both Point and Multipoint layers.

| Preset | Geometry | Symbol                                                                                       | Fill | Stroke | Width |
|--------|------|----------------------------------------------------------------------------------------------|------|--------|-------|
| `land` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#EAE3D2;--stroke:#C9BFA8;--w:3.0px"></span>  | <span class="as-swatch" style="background:#EAE3D2"></span> `#EAE3D2` | <span class="as-swatch" style="background:#C9BFA8"></span> `#C9BFA8` | 0.70  |
| `lake` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#A9D3E8;--stroke:#7FB3CE;--w:2.5px"></span>  | <span class="as-swatch" style="background:#A9D3E8"></span> `#A9D3E8` | <span class="as-swatch" style="background:#7FB3CE"></span> `#7FB3CE` | 0.95  |
| `ocean` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#8FC1DD;--stroke:#6BA8C9;--w:2.5px"></span>  | <span class="as-swatch" style="background:#8FC1DD"></span> `#8FC1DD` | <span class="as-swatch" style="background:#6BA8C9"></span> `#6BA8C9` | 0.95  |
| `forest` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#A7C293;--stroke:#87A86C;--w:2.5px"></span>  | <span class="as-swatch" style="background:#A7C293"></span> `#A7C293` | <span class="as-swatch" style="background:#87A86C"></span> `#87A86C` | 0.70  |
| `park` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#C8E2AF;--stroke:#A8C98D;--w:2.5px"></span>  | <span class="as-swatch" style="background:#C8E2AF"></span> `#C8E2AF` | <span class="as-swatch" style="background:#A8C98D"></span> `#A8C98D` | 0.70  |
| `wetland` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#C2D6C4;--stroke:#A0BCA2;--w:2.5px"></span>  | <span class="as-swatch" style="background:#C2D6C4"></span> `#C2D6C4` | <span class="as-swatch" style="background:#A0BCA2"></span> `#A0BCA2` | 0.70  |
| `sand` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#F0E2BE;--stroke:#DBC999;--w:2.5px"></span>  | <span class="as-swatch" style="background:#F0E2BE"></span> `#F0E2BE` | <span class="as-swatch" style="background:#DBC999"></span> `#DBC999` | 0.70  |
| `glacier` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#E9F3F6;--stroke:#CADDE3;--w:2.5px"></span>  | <span class="as-swatch" style="background:#E9F3F6"></span> `#E9F3F6` | <span class="as-swatch" style="background:#CADDE3"></span> `#CADDE3` | 0.70  |
| `urban` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#E6DAD2;--stroke:#CDBDB0;--w:2.5px"></span>  | <span class="as-swatch" style="background:#E6DAD2"></span> `#E6DAD2` | <span class="as-swatch" style="background:#CDBDB0"></span> `#CDBDB0` | 0.70  |
| `building` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#D8C7BA;--stroke:#B6A393;--w:2.5px"></span>  | <span class="as-swatch" style="background:#D8C7BA"></span> `#D8C7BA` | <span class="as-swatch" style="background:#B6A393"></span> `#B6A393` | 0.95  |
| `farmland` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#E9E4B0;--stroke:#C7BE7A;--w:2.5px"></span>  | <span class="as-swatch" style="background:#E9E4B0"></span> `#E9E4B0` | <span class="as-swatch" style="background:#C7BE7A"></span> `#C7BE7A` | 0.70  |
| `desert` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#F3E2C0;--stroke:#D9C190;--w:2.5px"></span>  | <span class="as-swatch" style="background:#F3E2C0"></span> `#F3E2C0` | <span class="as-swatch" style="background:#D9C190"></span> `#D9C190` | 0.70  |
| `industrial` | Polygon | <span class="as-sym as-sym--poly" style="--fill:#DCD4DE;--stroke:#B7AABA;--w:2.5px"></span>  | <span class="as-swatch" style="background:#DCD4DE"></span> `#DCD4DE` | <span class="as-swatch" style="background:#B7AABA"></span> `#B7AABA` | 0.70  |
| `admin` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#3C3C3C;--w:2px"></span>                   | none | <span class="as-swatch" style="background:#3C3C3C"></span> `#3C3C3C` | 1.65  |
| `admin_bold` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#1E1E1E;--w:4px"></span>                   | none | <span class="as-swatch" style="background:#1E1E1E"></span> `#1E1E1E` | 3.50  |
| `admin_subtle` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#9B9B9B;--w:1.5px"></span>                 | none | <span class="as-swatch" style="background:#9B9B9B"></span> `#9B9B9B` | 0.95  |
| `river` | Line | <span class="as-sym as-sym--line" style="--stroke:#5B9BC4;--w:2.5px"></span>                 | none | <span class="as-swatch" style="background:#5B9BC4"></span> `#5B9BC4` | 2.35  |
| `stream` | Line | <span class="as-sym as-sym--line" style="--stroke:#8FBFD9;--w:2px"></span>                   | none | <span class="as-swatch" style="background:#8FBFD9"></span> `#8FBFD9` | 1.15  |
| `coastline` | Line | <span class="as-sym as-sym--line" style="--stroke:#4A8FB5;--w:2px"></span>                   | none | <span class="as-swatch" style="background:#4A8FB5"></span> `#4A8FB5` | 1.15  |
| `road` | Line | <span class="as-sym as-sym--line" style="--stroke:#8C8C8C;--w:2.5px"></span>                 | none | <span class="as-swatch" style="background:#8C8C8C"></span> `#8C8C8C` | 2.80  |
| `highway` | Line | <span class="as-sym as-sym--line" style="--stroke:#E8A33D;--w:3.5px"></span>                 | none | <span class="as-swatch" style="background:#E8A33D"></span> `#E8A33D` | 4.65  |
| `railway` | Line | <span class="as-sym as-sym--line" style="--stroke:#6B6B6B;--w:2px"></span>                   | none | <span class="as-swatch" style="background:#6B6B6B"></span> `#6B6B6B` | 1.85  |
| `trail` | Line | <span class="as-sym as-sym--line" style="--stroke:#B5651D;--w:2px"></span>                   | none | <span class="as-swatch" style="background:#B5651D"></span> `#B5651D` | 1.40  |
| `boundary` | Line | <span class="as-sym as-sym--line" style="--stroke:#9C8BA8;--w:2px"></span>                   | none | <span class="as-swatch" style="background:#9C8BA8"></span> `#9C8BA8` | 1.85  |
| `contour` | Line | <span class="as-sym as-sym--line" style="--stroke:#B5905C;--w:1px"></span>                   | none | <span class="as-swatch" style="background:#B5905C"></span> `#B5905C` | 0.50  |
| `cycleway` | Line | <span class="as-sym as-sym--line" style="--stroke:#2E8B8B;--w:1.5px"></span>                 | none | <span class="as-swatch" style="background:#2E8B8B"></span> `#2E8B8B` | 1.20  |
| `power` | Line | <span class="as-sym as-sym--line" style="--stroke:#9A9A9A;--w:1.5px"></span>                 | none | <span class="as-swatch" style="background:#9A9A9A"></span> `#9A9A9A` | 1.00  |
| `city` | Point | <span class="as-sym as-sym--point" style="--fill:#4D4D4D;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#4D4D4D"></span> `#4D4D4D` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `town` | Point| <span class="as-sym as-sym--point" style="--fill:#7A7A7A;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#7A7A7A"></span> `#7A7A7A` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `peak` | Point| <span class="as-sym as-sym--point" style="--fill:#8B5E3C;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#8B5E3C"></span> `#8B5E3C` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `poi` | Point| <span class="as-sym as-sym--point" style="--fill:#C0392B;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#C0392B"></span> `#C0392B` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `spring` | Point| <span class="as-sym as-sym--point" style="--fill:#5B9BC4;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#5B9BC4"></span> `#5B9BC4` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `airport` | Point| <span class="as-sym as-sym--point" style="--fill:#3B6FB0;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#3B6FB0"></span> `#3B6FB0` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `camp` | Point| <span class="as-sym as-sym--point" style="--fill:#5E7F3C;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#5E7F3C"></span> `#5E7F3C` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |
| `harbor` | Point| <span class="as-sym as-sym--point" style="--fill:#2C5F7C;--stroke:#666666;--w:1.5px"></span> | <span class="as-swatch" style="background:#2C5F7C"></span> `#2C5F7C` | <span class="as-swatch" style="background:#666666"></span> `#666666` | 0.70  |

---

## Highlights

Bright hollow Polygon presets for call-outs and selections, with no fill over a
saturated `2.0` pt outline. They zero the fill opacity, so the body renders
hollow on a Polygon or Point. Designed for **Polygon** layers; with the default
`strict_geom=False` they may still be applied to other geometries (on a Polyline
the outline color becomes the line). `highlight` with no hue is an alias for
`highlight_red`.

| Preset | Geometry | Symbol | Stroke | Width |
|--------|----------|--------|--------|-------|
| `highlight` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#E31A1C;--w:3.5px"></span> | <span class="as-swatch" style="background:#E31A1C"></span> `#E31A1C` | 2.5   |
| `highlight_red` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#E31A1C;--w:3.5px"></span> | <span class="as-swatch" style="background:#E31A1C"></span> `#E31A1C` | 2.5   |
| `highlight_orange` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#FF7A00;--w:3.5px"></span> | <span class="as-swatch" style="background:#FF7A00"></span> `#FF7A00` | 2.5   |
| `highlight_yellow` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#FFD400;--w:3.5px"></span> | <span class="as-swatch" style="background:#FFD400"></span> `#FFD400` | 2.5   |
| `highlight_green` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#39D353;--w:3.5px"></span> | <span class="as-swatch" style="background:#39D353"></span> `#39D353` | 2.5   |
| `highlight_teal` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#10C7B0;--w:3.5px"></span> | <span class="as-swatch" style="background:#10C7B0"></span> `#10C7B0` | 2.5   |
| `highlight_blue` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#1F8FFF;--w:3.5px"></span> | <span class="as-swatch" style="background:#1F8FFF"></span> `#1F8FFF` | 2.5   |
| `highlight_indigo` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#5B5BFF;--w:3.5px"></span> | <span class="as-swatch" style="background:#5B5BFF"></span> `#5B5BFF` | 2.5   |
| `highlight_purple` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#A14BFF;--w:3.5px"></span> | <span class="as-swatch" style="background:#A14BFF"></span> `#A14BFF` | 2.5   |
| `highlight_pink` | Polygon | <span class="as-sym as-sym--poly" style="--stroke:#FF2D95;--w:3.5px"></span> | <span class="as-swatch" style="background:#FF2D95"></span> `#FF2D95` | 2.5   |


<br><br><br><br><br>