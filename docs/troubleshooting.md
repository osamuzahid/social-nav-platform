# Troubleshooting

**Leftover `/clock`.** `--execute` refuses to start if `/clock` is already on the domain. Close the previous Isaac / Kit process, then retry. Prefer `config/planners/fastrtps_no_shm.xml` when Fast DDS shared-memory locks break `/clock`.

**Missing USDs.** Doctor prints `FAIL unpacked USDs missing`. Run `./scripts/unpack-assets.sh` with the tarball at `social-nav-assets/dist/prebuilt-assets-v0.1.0-candidate.tar.zst`.

**Snapshot apt `NO_PUBKEY`.** `snapshots.ros.org` is not signed by
`ros-archive-keyring.gpg`. Use family `v0.2.7`. Bootstrap installs
the vendored Snapshot builder key to `/usr/share/keyrings/ros-snapshot-keyring.gpg`.
If `apt-get update` still fails, bootstrap removes
`/etc/apt/sources.list.d/social-nav-ros-snapshot.list` so ordinary apt keeps
working. Do not point the snapshot line at the live ROS keyring.

**Sibling SHA mismatch.** Doctor compares each sibling `HEAD` to `components.lock.yaml`. Check out the locked SHA (or the family tag that matches the lock) before running hops.

**Isaac abort `PyFloat_Check` on `Agent.yaw`.** Overlay `hunav_msgs` was not
Release. `./scripts/build.sh` pins `-DCMAKE_BUILD_TYPE=Release` (`-DNDEBUG`).
Do not mix an empty-type colcon overlay into `--execute`.

**HuNav / ESC overlay.** `--execute` needs `hunav_agent_manager` on the overlay. After `./scripts/build.sh`, that is `../hunav-sim-jazzy/install/setup.bash`. Otherwise set `SOCIAL_NAV_ROS_SETUP` (and `SOCIAL_NAV_ESC_SETUP` for ESC hops).

**Sourcing ROS with `set -u`.** Ament setup files can abort. `./scripts/build.sh` sources with `set +u`. Do the same in an interactive shell if you `source /opt/ros/jazzy/setup.bash` under `set -u`.

**Refuse overwrite.** `results/runs/<id>/` already has files. Pick another experiment or remove that archive directory. Do not rerun a succeeded ID in place.

**`bt_navigator` disappeared.** The supervisor exits with `planner_startup_error` instead of hanging. Restart the hop after Nav2 is healthy.

**SIGINT in a bash background job.** `cmd &` ignores SIGINT. Run hops in the foreground, or send SIGINT to the supervisor process group.

**Isaac path.** Default is `$HOME/isaacsim/python.sh`. Override with `SOCIAL_NAV_ISAAC_PATH`.

**Nav2 and ESC together.** Never. Each experiment ID is one stack.

**PhysX Stretch.** `stretch_wheeled` is rejected. Use kinematic Stretch (`Physics=none`).
