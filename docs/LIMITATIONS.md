# Limitations (v0.1.0-candidate)

- Native Isaac startup, Nav2/ESC child supervision, and result archival are
  not wired. `social-nav run --execute` fails closed.
- Bootstrap is check-only unless `--install-system-deps` (apt only).
- Sibling handover trees are expected next to this checkout. There is no
  GitHub clone step on this candidate.
- PhysX Stretch (`stretch_wheeled`) is rejected.
- Simultaneous multi-robot episodes are out of scope.
- Mixed HuNav behaviour trees are not scored (campaign crowds are type 2).
- CUCR historical world SHAs, `lightsfm` git SHA, and lab org URLs stay
  unknown.
