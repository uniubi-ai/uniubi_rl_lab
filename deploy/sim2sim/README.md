# Local MuJoCo Sim2Sim

[中文文档](README.zh-CN.md)

This directory contains a local MuJoCo sim2sim runner for Cyvet. It loads the same `rsl_rl` actor-critic checkpoint format used by Isaac Lab training.

## Scope

The current runner is intended for local policy playback and quick sim2sim checks.

- Robot: Cyvet
- Policy backend: `rsl_rl` actor-critic checkpoint
- Control input: command-line velocity command
- MuJoCo actuator: explicit torque PD

The MuJoCo model uses the Cyvet XML assets under `deploy/sim2sim/assets/cyvet/`. The runner disables the XML position actuator gains at startup and applies PD torque directly. The actuator parameters in `control.actuator_model` mirror the Cyvet actuator used during Isaac Lab training, including armature, torque-speed limits, and friction terms.

## Runtime

Install the sim2sim Python dependencies:

```bash
python -m pip install -r deploy/sim2sim/requirements.txt
```

## Configuration

Set the checkpoint in `deploy/sim2sim/configs/cyvet.yaml` before running:

```yaml
policy:
  checkpoint: logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt
```

The default command is also stored in the same config:

```yaml
commands:
  lin_vel_x: 0.5
  lin_vel_y: 0.0
  ang_vel_z: 0.0
```

You can override the command from the CLI.

The default actuator delay is zero:

```yaml
control:
  delay_steps: 0
```

## Usage

Run with the MuJoCo viewer:

```bash
python deploy/sim2sim/play_mujoco.py \
  --config deploy/sim2sim/configs/cyvet.yaml \
  --cmd-vx 0.5 \
  --cmd-vy 0.0 \
  --cmd-yaw 0.0
```

Validate the config without starting MuJoCo:

```bash
python deploy/sim2sim/play_mujoco.py \
  --config deploy/sim2sim/configs/cyvet.yaml \
  --dry-run
```

## Notes

- Joint states are reordered between MuJoCo leg-major order and the policy joint order.
- The policy observation matches the 45-dimensional actor observation used by the Isaac Lab task.
- The runner uses explicit torque PD and clips torque with the configured torque-speed curve and `control.torque_limit`.
- Commands are passed from the CLI or YAML.
- This local runner does not use the Uniubi SDK. For SDK-level sim2sim, see [../README.md](../README.md).
