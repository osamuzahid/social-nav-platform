# Installation

Supported runtime: **Ubuntu 24.04 x86-64**, **ROS 2 Jazzy**, **NVIDIA Isaac Sim 6.0.1** (workstation install). One robot per episode. Cameras stay on.

The lab checkout is five sibling directories. Clone or copy them next to each other:

```text
<workspace>/
├── social-nav-platform
├── hunav-isaac-wrapper-jazzy
├── hunav-sim-jazzy
├── esc-nav-jazzy
└── social-nav-assets
```

Exact SHAs: [components.lock.yaml](../components.lock.yaml). Isaac Sim is not in git. World and robot USDs ship as a checksummed tarball, not Git LFS.

## 1. System packages

Isaac Sim must already be installed (default `~/isaacsim/python.sh`, or set `SOCIAL_NAV_ISAAC_PATH`).

```bash
source /opt/ros/jazzy/setup.bash
sudo ./scripts/bootstrap.sh --install-system-deps
```

HuNav also needs **lightsfm** headers at `/usr/local/include/lightsfm` (build [robotics-upo/lightsfm](https://github.com/robotics-upo/lightsfm) and install into `/usr/local`).

## 2. Prebuilt USDs

Place `dist/prebuilt-assets-v0.1.0-candidate.tar.zst` under `social-nav-assets/` (checksum in that repo’s `SHA256SUMS` and in the lock file). Then:

```bash
./scripts/unpack-assets.sh
```

Occupancy maps and octomaps are already in git under `social-nav-assets/maps/`.

## 3. Build overlays

```bash
source /opt/ros/jazzy/setup.bash
./scripts/build.sh
```

This colcon-builds platform `people_msgs` / `pedsim_msgs`, then HuNav, the Isaac wrapper, then ESC. `./scripts/build.sh` sources ROS with `set +u` so Ament setup files do not abort.

After a successful build, `--execute` finds HuNav at `../hunav-sim-jazzy/install/setup.bash` and ESC at `../esc-nav-jazzy/install/setup.bash`. You do not need `SOCIAL_NAV_ROS_SETUP` unless those overlays live somewhere else.

## 4. Check

```bash
./scripts/doctor.sh
./scripts/test.sh
./scripts/social-nav validate
```

Doctor fails if a sibling `HEAD` does not match the lock, if campaign USDs are missing, or if the tarball checksum is wrong.

Continue with [quickstart.md](quickstart.md).
