# Installation

Supported runtime: **Ubuntu 24.04 x86-64**, **ROS 2 Jazzy**, **NVIDIA Isaac Sim 6.0.1** (workstation install). One robot per episode. Cameras stay on.

Bootstrap installs the lock apt set (Nav2 and related debs). It does **not** install the NVIDIA driver, Isaac Sim, ROS 2 itself, or lightsfm. Put those on the machine first.

Exact sibling SHAs, apt pins, and host notes: [components.lock.yaml](../components.lock.yaml) (`v0.2.7` matches). Isaac Sim is not in git. World and robot USDs ship as a checksummed tarball, not Git LFS.

## Host prerequisites (install by hand)

Do this before cloning. Doctor reports Isaac / driver / lightsfm / pandas / numpy as **notes**; missing Isaac or lightsfm still fails `--execute` / `build.sh`.

### Have these first

| Need | Pin | How |
|---|---|---|
| OS | Ubuntu **24.04** x86-64 (`noble`) | [Isaac Sim 6.0.1 requirements](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/requirements.html) |
| GPU | NVIDIA GPU with **RT cores** (A100/H100 not supported for rendering) | NVIDIA minimums: 32 GB RAM, 16 GB VRAM. Laptops below that can still run windowed hops (lag is accepted). |
| Driver | **≥ 595.58.03** (R595). Tested **595.84** | `nvidia-smi`. Reboot after install. |
| Isaac Sim | **6.0.1** standalone. Tested `VERSION` `6.0.1-rc.7+release.42383.32955d8d.gl` | [Workstation install](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/install_workstation.html). Unpack so `~/isaacsim/python.sh` exists (or set `SOCIAL_NAV_ISAAC_PATH`). First run: accept the EULA, or `export OMNI_KIT_ACCEPT_EULA=YES`. |
| ROS 2 | **Jazzy** at `/opt/ros/jazzy/setup.bash`. Python **3.12** | [Jazzy Ubuntu debs](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) (`ros-jazzy-desktop` is enough). Nav2 **1.3.12** is then pinned by bootstrap from the lock snapshot, not from rolling `packages.ros.org`. |
| lightsfm | Headers at `/usr/local/include/lightsfm` (`sfm.hpp`) | Header-only. Git SHA of the freeze install is **unknown** — do not guess one. Clone [robotics-upo/lightsfm](https://github.com/robotics-upo/lightsfm), then `make && sudo make install`. Doctor compares the include-tree sha256 in the lock as a note. |
| pandas / numpy | Tested **2.1.4** / **1.26.4** | `sudo apt install python3-pandas python3-numpy` (not in `apt.packages`; evaluator uses them). |
| GitHub | The five remotes are **public** | SSH or HTTPS. |
| USD download | GitHub CLI **or** a browser | `gh` is used below. The tarball is Release **`v0.2.1`** on `social-nav-assets`. |

### Machine this family was built and tested on

Same lock `environment` block. A second Ubuntu is not required if this host matches.

| Item | Value |
|---|---|
| OS | Ubuntu 24.04 (`noble`), x86_64 |
| NVIDIA driver | 595.84 (minimum 595.58.03) |
| Isaac Sim | 6.0.1-rc.7+release.42383.32955d8d.gl at `~/isaacsim` |
| Python | 3.12.3 (system) |
| pandas / numpy | 2.1.4 / 1.26.4 |
| Nav2 | `ros-jazzy-navigation2` **1.3.12** (snapshot `jazzy/2026-06-18`) |
| BehaviorTree.CPP | 4.9.0 |
| Assimp | `assimp-utils` 5.3.1+ds-2build1 (convert path; not needed to run hops) |
| OctoMap | `liboctomap-dev` 1.9.7+dfsg-3.1build3 |
| lightsfm | `/usr/local/include/lightsfm` (revision unknown; include sha256 in the lock) |

## Family tags

The five remotes are one product. A **family tag** is the same name on all
five (`v0.2.7` today) so a clone is a matched set. Doctor checks the sibling
**SHAs** in [components.lock.yaml](../components.lock.yaml), not the tag
object. This is a checkout pin, not an API version.

**Why they exist.** `build.sh` and `--execute` assume the four siblings are
exactly those lock SHAs. The tag is how you get that set without picking
commits by hand.

**Install.** Clone every sibling at the tag in the commands below. Do not mix
tags. Do not clone `main` on one tree and a tag on another. After install,
stay on that checkout — day-to-day hops do not need other tags.

**When to tag.** Move or cut the family tag when `git clone --branch` must
include the change (lock sibling SHAs, or front-door install docs). Same
name on all five remotes. Sibling SHAs unchanged: retag platform only.
Sibling SHAs changed: new tag name on all five and update the lock. Do not
mix tags. Do not clone `v0.2.4` / `v0.2.3` / `v0.2.2`.

**Not the family tag.** The USD tarball is GitHub Release **`v0.2.1`** on
`social-nav-assets`. That number is the world/robot bundle.

## Clone the family

```bash
mkdir -p ~/social-nav && cd ~/social-nav
git clone --branch v0.2.7 git@github.com:osamuzahid/social-nav-platform.git
git clone --branch v0.2.7 git@github.com:osamuzahid/hunav-isaac-wrapper-jazzy.git
git clone --branch v0.2.7 git@github.com:osamuzahid/hunav-sim-jazzy.git
git clone --branch v0.2.7 git@github.com:osamuzahid/esc-nav-jazzy.git
git clone --branch v0.2.7 git@github.com:osamuzahid/social-nav-assets.git
```

```text
<workspace>/
├── social-nav-platform
├── hunav-isaac-wrapper-jazzy
├── hunav-sim-jazzy
├── esc-nav-jazzy
└── social-nav-assets
```

Do not clone `v0.2.4` (empty `CMAKE_BUILD_TYPE`; Isaac abort `PyFloat_Check` on `Agent.yaw`). Do not clone `v0.2.3` (snapshot signed with the live ROS keyring). Do not clone `v0.2.2` (unpinned apt).

## 1. System packages

`--install-system-deps` installs the apt versions in
[components.lock.yaml](../components.lock.yaml) (`apt.packages`) so the host
matches the stack this family was built and tested against, then holds those
packages. The lock’s `ros_snapshot` is the archive that serves the ROS debs.
That archive is signed by the ROS Snapshot builder key vendored at
`config/apt/ros-snapshot.asc`, not by the live `packages.ros.org` keyring.

Jazzy must already be on the machine (`/opt/ros/jazzy/setup.bash`). Bootstrap does not install Isaac Sim or lightsfm.

```bash
cd social-nav-platform
source /opt/ros/jazzy/setup.bash
sudo ./scripts/bootstrap.sh --install-system-deps
```

## 2. Prebuilt USDs

The USD bundle is unchanged from the `v0.2.1` Release (same sha256 as the lock).
Download that asset, then unpack:

```bash
mkdir -p ../social-nav-assets/dist
gh release download v0.2.1 --repo osamuzahid/social-nav-assets \
  --pattern 'prebuilt-assets-*.tar.zst' -D ../social-nav-assets/dist
./scripts/unpack-assets.sh
```

Checksum is in `social-nav-assets/SHA256SUMS` and in the lock file. Occupancy maps and octomaps are already in git under `social-nav-assets/maps/`.

## 3. Build overlays

```bash
source /opt/ros/jazzy/setup.bash
./scripts/build.sh
```

This colcon-builds platform `people_msgs` / `pedsim_msgs`, then HuNav, the Isaac wrapper, then ESC. Every `colcon` invocation passes `-DCMAKE_BUILD_TYPE=Release` so `hunav_msgs` matches the freeze overlay (`-DNDEBUG`; empty type leaves rosidl `PyFloat_Check` on `Agent.yaw` and abort()s Isaac). `./scripts/build.sh` sources ROS with `set +u` so Ament setup files do not abort.

After a successful build, `--execute` finds HuNav at `../hunav-sim-jazzy/install/setup.bash` and ESC at `../esc-nav-jazzy/install/setup.bash`. You do not need `SOCIAL_NAV_ROS_SETUP` unless those overlays live somewhere else.

## 4. Check

```bash
./scripts/doctor.sh
./scripts/test.sh
./scripts/social-nav validate
```

Doctor fails if a sibling `HEAD` does not match the lock, if campaign USDs are missing, if the tarball checksum is wrong, or if a lock apt package is installed at a different version. Isaac, Python, pandas/numpy, Assimp, NVIDIA driver, and lightsfm headers are compared to `environment` in the lock as notes; they do not fail the check.

Continue with [quickstart.md](quickstart.md).
