# Uniubi RL Lab

[中文文档](README.zh-CN.md)

Uniubi RL Lab is a simulation training project for Uniubi robots. It currently includes the Cyvet quadruped robot.

## Overview

<p align="center">
  <img src="docs/media/cyvet_isaaclab.gif" width="640" alt="Cyvet quadruped running in Isaac Lab">
</p>

Current task:

```text
Uniubi-Cyvet-Velocity
```

## Features

This repository includes:

- Cyvet USD robot asset loading.
- Uniubi explicit actuator model with Cyvet actuator parameters.
- A velocity-tracking locomotion task based on Isaac Lab manager-based environments.
- RSL-RL PPO configuration with an MLP actor-critic.
- Train, play, zero-agent, random-agent, and task-list scripts.
- Deployment documents for policy export, local MuJoCo sim2sim, SDK sim2sim, and sim2real.

## Versions

Current development and validation use:

- Python 3.11
- Isaac Sim 5.1
- Isaac Lab 2.3.2
- PyTorch 2.7.0 CUDA 12.8
- RSL-RL 3.0.1 or newer

## Installation

Create and activate a Python environment:

```bash
conda create -n env_isaaclab_5.1 python=3.11 -y
conda activate env_isaaclab_5.1
```

Install Isaac Sim, Isaac Lab, and their dependencies by following the official Isaac Lab guide:

[Isaac Lab 2.3.2 pip installation](https://isaac-sim.github.io/IsaacLab/v2.3.2/source/setup/installation/pip_installation.html)

After Isaac Lab is installed, install this repository in editable mode:

```bash
cd /path/to/uniubi_rl_lab
python -m pip install -e source/uniubi_rl_lab
```

On the first Isaac Sim launch, NVIDIA Omniverse may ask for EULA acceptance. Run this once in an interactive terminal:

```bash
python -c "import isaacsim"
```

Type `Yes` when prompted.

## Verify Installation

List registered Uniubi tasks:

```bash
python scripts/list_envs.py
```

Run a small smoke training job:

```bash
python scripts/rsl_rl/train.py \
  --task=Uniubi-Cyvet-Velocity \
  --headless \
  --num_envs=16 \
  --max_iterations=1 \
  --device cuda:0
```

The expected environment summary includes:

```text
Physics step-size     : 0.004
Environment step-size : 0.02
Active Action Terms (shape: 12)
policy observation shape: 45
critic observation shape: 60
```

## Training

Start a full PPO training run:

```bash
python scripts/rsl_rl/train.py \
  --task=Uniubi-Cyvet-Velocity \
  --headless \
  --device cuda:0 \
  --run_name cyvet_velocity
```

For debugging, reduce the number of environments and iterations:

```bash
python scripts/rsl_rl/train.py \
  --task=Uniubi-Cyvet-Velocity \
  --headless \
  --device cuda:0 \
  --num_envs=1024 \
  --max_iterations=1000 \
  --run_name debug
```

Training logs are written to:

```text
logs/rsl_rl/cyvet_velocity/<timestamp>_<run_name>/
```

Each run stores:

- `params/env.yaml`
- `params/agent.yaml`
- TensorBoard event files
- `model_*.pt` checkpoints
- Isaac Lab runtime logs under `isaaclab/`
- a git diff snapshot under `git/`

## Play

`play.py` uses `quality` rendering by default and samples velocity commands from the full play range.

Run a trained checkpoint:

```bash
python scripts/rsl_rl/play.py \
  --task=Uniubi-Cyvet-Velocity \
  --checkpoint logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt \
  --num_envs=32
```

Run without rendering:

```bash
python scripts/rsl_rl/play.py \
  --task=Uniubi-Cyvet-Velocity \
  --checkpoint logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt \
  --num_envs=32 \
  --headless
```

## Deployment

Deployment documents are grouped under:

[deploy/README.md](deploy/README.md)

Available deployment topics:

- ONNX export from a trained checkpoint.
- Local MuJoCo sim2sim playback for Cyvet.
- Optional SDK sim2sim through `uniubi_robot_mock`.
- Sim2Real notes.

## Debug Agents

Zero-action and random-action scripts can be used to check reset, step, action dimensions, and contact setup:

```bash
python scripts/zero_agent.py --task=Uniubi-Cyvet-Velocity --num_envs=16 --headless
python scripts/random_agent.py --task=Uniubi-Cyvet-Velocity --num_envs=16 --headless
```

## Task Details

See [docs/cyvet_locomotion.md](docs/cyvet_locomotion.md) for Cyvet asset, actuator, observation, reward, and timing details.

## License

Original Uniubi source code in this repository is licensed under the Apache License 2.0.
Files derived from or adapted from Isaac Lab retain their BSD-3-Clause notices.
Files with their own SPDX identifier, copyright header, or license notice remain under those terms.
See [LICENSE](LICENSE), [NOTICE](NOTICE), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Repository Layout

```text
source/uniubi_rl_lab/uniubi_rl_lab/assets/robots/
  uniubi.py
  uniubi_actuators.py
  cyvet/cyvet.usd

source/uniubi_rl_lab/uniubi_rl_lab/tasks/locomotion/
  agents/rsl_rl_ppo_cfg.py
  mdp/
  robots/cyvet/cyvet_env_cfg.py

scripts/
  list_envs.py
  zero_agent.py
  random_agent.py
  rsl_rl/train.py
  rsl_rl/play.py

deploy/
  README.md
  sim2sim/play_mujoco.py
  sim2sim/configs/cyvet.yaml
  sim2real/README.md
```

## Troubleshooting

If training fails with a permission error under `/tmp/isaaclab/logs`, make sure you are using this repository's `scripts/rsl_rl/train.py`. It redirects Isaac Lab runtime logs into the current run directory.

If the process stops before task initialization and prints an Omniverse EULA prompt, run:

```bash
python -c "import isaacsim"
```

and accept the EULA in an interactive terminal.

If the task cannot be found, reinstall the extension:

```bash
python -m pip install -e source/uniubi_rl_lab
python scripts/list_envs.py
```
