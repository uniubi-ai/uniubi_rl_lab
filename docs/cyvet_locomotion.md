# Cyvet Locomotion Task

[中文文档](cyvet_locomotion.zh-CN.md)

This document describes the Cyvet velocity-tracking task in Uniubi RL Lab.

## Task

```text
Uniubi-Cyvet-Velocity
```

The task trains a Cyvet quadruped to track planar base velocity commands with an MLP policy and RSL-RL PPO.

Entry points:

```text
env_cfg_entry_point: uniubi_rl_lab.tasks.locomotion.robots.cyvet.cyvet_env_cfg:CyvetEnvCfg
play_env_cfg_entry_point: uniubi_rl_lab.tasks.locomotion.robots.cyvet.cyvet_env_cfg:CyvetPlayEnvCfg
rsl_rl_cfg_entry_point: uniubi_rl_lab.tasks.locomotion.agents.rsl_rl_ppo_cfg:PPORunnerCfg
```

## Robot Asset

Cyvet is loaded from a local USD file:

```text
source/uniubi_rl_lab/uniubi_rl_lab/assets/robots/cyvet/cyvet.usd
```

Robot config:

```text
source/uniubi_rl_lab/uniubi_rl_lab/assets/robots/uniubi.py
```

Names used by the task config:

```text
base body: BASE_LINK
feet:      .*FOOT_LINK
joints:    .*_ABAD_JOINT, .*_HIP_JOINT, .*_KNEE_JOINT
```

## Actuator

Cyvet currently uses:

```text
UniubiActuatorCfg_Cyvet
```

Implementation:

```text
source/uniubi_rl_lab/uniubi_rl_lab/assets/robots/uniubi_actuators.py
```

Current nominal parameters:

```text
X1 = 15.0
X2 = 21.0
Y1 = 48.0
Y2 = 48.0
Va = 0.01
```

The actuator includes:

- delayed PD control
- torque-speed clipping
- explicit static and dynamic friction
- per-joint armature, static friction, and dynamic friction parameters

The current open-source configuration does not include backlash or dead-zone logic.

## Timing

Current task timing:

```text
sim.dt     = 0.004 s
decimation = 5
env step   = 0.004 * 5 = 0.02 s
episode    = 20.0 s
max episode length = 20.0 / 0.02 = 1000 env steps
```

Rates:

```text
physics rate = 250 Hz
policy rate  = 50 Hz
```

## Observations

Policy observation shape:

```text
45
```

Policy terms:

- base angular velocity
- projected gravity
- velocity command
- relative joint position
- relative joint velocity
- last action

Critic observation shape:

```text
60
```

Critic additionally includes:

- base linear velocity
- joint effort

## Actions

Action shape:

```text
12
```

The action is a joint position target offset for:

```text
.*_ABAD_JOINT
.*_HIP_JOINT
.*_KNEE_JOINT
```

Current action scale:

```text
0.25
```

## Commands

Command term:

```text
base_velocity
```

Initial command range:

```text
lin_vel_x: (-0.1, 0.1)
lin_vel_y: (-0.1, 0.1)
ang_vel_z: (-1.0, 1.0)
```

Limit range:

```text
lin_vel_x: (-1.0, 1.0)
lin_vel_y: (-0.4, 0.4)
ang_vel_z: (-1.0, 1.0)
```

The linear velocity curriculum expands the command range according to tracking performance.

## Rewards

Main positive tracking terms:

- `track_lin_vel_xy`
- `track_ang_vel_z`

Main penalties:

- base z linear velocity
- base roll/pitch angular velocity
- joint velocity
- joint acceleration
- joint torque
- action rate
- joint position limits
- energy
- flat orientation
- joint position deviation
- feet air-time variance
- feet slide
- undesired contacts

## Terminations

Enabled terminations:

- timeout
- base contact
- bad orientation

With the current timing, a 20-second episode corresponds to 1000 environment steps. A stable policy should have `Mean episode length` close to 1000, and most episodes should end by timeout.

## PPO Config

PPO config:

```text
source/uniubi_rl_lab/uniubi_rl_lab/tasks/locomotion/agents/rsl_rl_ppo_cfg.py
```

Current network:

```text
actor:  [512, 256, 128]
critic: [512, 256, 128]
activation: elu
```

Current runner defaults:

```text
num_steps_per_env = 24
max_iterations = 50000
save_interval = 100
experiment_name = cyvet_velocity
```

## Monitoring

Tail training logs:

```bash
tail -f logs/rsl_rl/cyvet_velocity/<run>/isaaclab/*.log
```

If the run was started in the background with a separate stdout file, tail that stdout file instead.

Start TensorBoard:

```bash
tensorboard --logdir logs/rsl_rl/cyvet_velocity --host 0.0.0.0 --port 6006
```

Suggested metrics:

- `Mean reward`
- `Mean episode length`
- `Metrics/base_velocity/error_vel_xy`
- `Metrics/base_velocity/error_vel_yaw`
- `Episode_Termination/time_out`
- `Episode_Termination/base_contact`
- `Episode_Termination/bad_orientation`
