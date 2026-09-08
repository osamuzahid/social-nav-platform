# Contributing

- Keep scored hops at one robot, cameras on, lidar on.
- Pin sibling trees with exact SHAs in `components.lock.yaml`. Do not pin branch tips.
- Do not add GNOME terminal farms or `pkill -f nav2_isaac_keepalive`.
- Do not hard-code a personal home directory.
- New worlds, robots, crowds, routes, and planners are YAML under `config/`.
  Register a matching `config/experiments/<id>.yaml`.
- `social-nav run --execute` runs one process group (Isaac, then Nav2 or ESC).
  Cameras stay on.

Licence: MIT for platform tools. Vendored msgs keep BSD texts in
`src/vendor/*/LICENSE`.
