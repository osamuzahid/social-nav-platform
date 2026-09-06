# Contributing

This tree is a local handover candidate. There is no public issue tracker yet.

- Keep scored hops at one robot, cameras on, lidar on.
- Use exact SHAs in `components.lock.yaml`. Do not pin branch tips.
- Do not add GNOME terminal farms or `pkill -f nav2_isaac_keepalive`.
- Do not hard-code a personal home directory.
- New worlds, robots, crowds, routes, and planners are YAML under `config/`.
  Register a matching `config/experiments/<id>.yaml`.
- Native Isaac execute is not wired. `social-nav run --execute` must keep
  failing closed until a single supervisor lands.

Licence: MIT for platform tools. Vendored msgs keep BSD texts in
`src/vendor/*/LICENSE`.
