# Platform notes

Front door for the lab handover family. Sibling trees:

| Lock key | Path (relative) | Tag |
|---|---|---|
| wrapper | `../hunav-isaac-wrapper-jazzy` | `v0.1.0-candidate` |
| hunav | `../hunav-sim-jazzy` | `v0.1.0-candidate` |
| esc | `../esc-nav-jazzy` | `v0.1.0-candidate` |
| assets | `../social-nav-assets` | `v0.1.0-candidate` |

Exact SHAs: [components.lock.yaml](../components.lock.yaml).

## Experiments

Fourteen IDs `{world}-{robot}-{esc|nav2}`:

- museum-reachy
- hospital-stretch
- office-reachy
- bookstore-stretch
- house_museum-reachy
- small_house-stretch
- small_warehouse-reachy

Git example results: museum Reachy and hospital Stretch `metrics_cited.csv`
only. The other five pairs are named config. Full 14 CSVs stay the private
campaign release.

## Run lifecycle (this candidate)

`social-nav run <id>` validates and writes `cache/sessions/.../plan.json`.
`--execute` prints `simulator_startup_error` and exits 3. One supervisor
process is Phase 6. Do not restore a GNOME terminal farm.

## Not in this tree

CUCR USD binaries (`social-nav-assets` bundle). Generic Isaac/HuNav runtime
(`hunav-isaac-wrapper-jazzy`). NVIDIA Isaac Sim.
