# Extending

Scored hops stay at **one robot**, **cameras on**, **lidar on**. Nav2 and ESC are separate experiment IDs. Pin sibling trees with exact SHAs in `components.lock.yaml`; do not pin branch tips.

Register every runnable hop as `config/experiments/<id>.yaml` (`schema_version: 1`, one `robots:` entry, `planner` in `nav2/smac-2d` or `esc/extended-social-comfort`).

## World

1. Add the composed USD and payloads to `social-nav-assets` (or extend the prebuilt bundle).
2. Add occupancy `maps/<world>.yaml` + `.png` and, for ESC, `maps/<world>.bt`.
3. Add `config/worlds/<world>.yaml` (`usd`, `occupancy`, `octomap`, `crowd`).
4. Add `config/routes/<world>-campaign.yaml` (spawn, goal, yaw).
5. Add `config/crowds/<world>_crowd.yaml`.
6. Add two experiment files: `<world>-<robot>-nav2` and `<world>-<robot>-esc`.

Keep occupancy free cells white. `world_to_grid` uses floor, not round.

## Robot

1. USD under `social-nav-assets/robots/<name>/<name>.usd`.
2. `config/robots/<name>/robot.yaml` (sensor links, kinematic chassis).
3. `config/planners/nav2_<name>.yaml` and `esc_<name>.yaml` — `robot_radius` must match the chassis.

Lab robots are Stretch and Reachy with planar drive (`Physics=none`). PhysX Stretch (`stretch_wheeled`) is rejected.

## Crowd

File: `config/crowds/<world>_crowd.yaml`. Campaign layout:

| Agents | Role |
|---|---|
| A1, A2 | Moving (`max_vel` > 0). Patrol longer than 5 m; briefly intersect the robot path. |
| A3, A4, A5 | Standing (`max_vel` 0). On the path the stack actually drives, staggered, ≥ 2 m apart and ≥ 2 m from spawn. |

Do not park a moving-agent goal within 1.3 m of a standing agent. Default behaviour is RegularNav (type 2) unless you set another BT.

## Planner

Nav2 profiles live in `config/planners/nav2_*.yaml` with BT XML `navigate_to_pose_w_replanning_20hz.xml`. ESC profiles live in `config/planners/esc_*.yaml`. A new planner name must be added to `PLANNERS` in `src/social_nav_runner/experiments.py` and given a bring-up module the supervisor can call.

## Metric

Campaign keys: `config/metrics/campaign-v1.yaml`. Point `metrics:` in the experiment YAML at a new file to change the evaluator set.
