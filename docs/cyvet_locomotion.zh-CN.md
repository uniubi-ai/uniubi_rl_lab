# Cyvet Locomotion 任务

[English](cyvet_locomotion.md)

本文档说明 Uniubi RL Lab 中的 Cyvet 速度跟踪任务。

## 任务名

```text
Uniubi-Cyvet-Velocity
```

该任务训练 Cyvet 四足机器人跟踪平面速度指令，策略网络为 MLP，训练算法为 RSL-RL PPO。

注册入口：

```text
env_cfg_entry_point: uniubi_rl_lab.tasks.locomotion.robots.cyvet.cyvet_env_cfg:CyvetEnvCfg
play_env_cfg_entry_point: uniubi_rl_lab.tasks.locomotion.robots.cyvet.cyvet_env_cfg:CyvetPlayEnvCfg
rsl_rl_cfg_entry_point: uniubi_rl_lab.tasks.locomotion.agents.rsl_rl_ppo_cfg:PPORunnerCfg
```

## 机器人资产

Cyvet 使用本地 USD 文件加载：

```text
source/uniubi_rl_lab/uniubi_rl_lab/assets/robots/cyvet/cyvet.usd
```

机器人配置文件：

```text
source/uniubi_rl_lab/uniubi_rl_lab/assets/robots/uniubi.py
```

任务配置中使用的 body 和 joint 名称：

```text
base body: BASE_LINK
feet:      .*FOOT_LINK
joints:    .*_ABAD_JOINT, .*_HIP_JOINT, .*_KNEE_JOINT
```

## 执行器

Cyvet 当前使用：

```text
UniubiActuatorCfg_Cyvet
```

实现位置：

```text
source/uniubi_rl_lab/uniubi_rl_lab/assets/robots/uniubi_actuators.py
```

当前标称参数：

```text
X1 = 15.0
X2 = 21.0
Y1 = 48.0
Y2 = 48.0
Va = 0.01
```

执行器包含：

- delayed PD control
- torque-speed clipping
- 显式静摩擦和动摩擦
- 分关节 armature、静摩擦和动摩擦参数

当前开源配置中不包含 backlash 或 dead-zone 逻辑。

## 时间设置

当前任务时间设置：

```text
sim.dt     = 0.004 s
decimation = 5
env step   = 0.004 * 5 = 0.02 s
episode    = 20.0 s
max episode length = 20.0 / 0.02 = 1000 env steps
```

对应频率：

```text
physics rate = 250 Hz
policy rate  = 50 Hz
```

## 观测

Policy 观测维度：

```text
45
```

Policy 观测项：

- base angular velocity
- projected gravity
- velocity command
- relative joint position
- relative joint velocity
- last action

Critic 观测维度：

```text
60
```

Critic 额外包含：

- base linear velocity
- joint effort

## 动作

动作维度：

```text
12
```

动作是以下关节的位置目标偏移：

```text
.*_ABAD_JOINT
.*_HIP_JOINT
.*_KNEE_JOINT
```

当前 action scale：

```text
0.25
```

## 指令

指令项：

```text
base_velocity
```

初始指令范围：

```text
lin_vel_x: (-0.1, 0.1)
lin_vel_y: (-0.1, 0.1)
ang_vel_z: (-1.0, 1.0)
```

最大指令范围：

```text
lin_vel_x: (-1.0, 1.0)
lin_vel_y: (-0.4, 0.4)
ang_vel_z: (-1.0, 1.0)
```

训练过程中，线速度 curriculum 会根据跟踪效果逐步扩展指令范围。

## 奖励

主要正向跟踪项：

- `track_lin_vel_xy`
- `track_ang_vel_z`

主要惩罚项：

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

## 终止条件

当前启用：

- timeout
- base contact
- bad orientation

在当前时间设置下，20 秒 episode 对应 1000 个 env step。策略稳定后，`Mean episode length` 应接近 1000，并且大部分 episode 应由 timeout 结束。

## PPO 配置

PPO 配置文件：

```text
source/uniubi_rl_lab/uniubi_rl_lab/tasks/locomotion/agents/rsl_rl_ppo_cfg.py
```

当前网络：

```text
actor:  [512, 256, 128]
critic: [512, 256, 128]
activation: elu
```

当前 runner 默认值：

```text
num_steps_per_env = 24
max_iterations = 50000
save_interval = 100
experiment_name = cyvet_velocity
```

## 训练监控

查看训练日志：

```bash
tail -f logs/rsl_rl/cyvet_velocity/<run>/isaaclab/*.log
```

如果训练是后台启动并单独保存 stdout，则查看对应 stdout 文件。

启动 TensorBoard：

```bash
tensorboard --logdir logs/rsl_rl/cyvet_velocity --host 0.0.0.0 --port 6006
```

建议关注：

- `Mean reward`
- `Mean episode length`
- `Metrics/base_velocity/error_vel_xy`
- `Metrics/base_velocity/error_vel_yaw`
- `Episode_Termination/time_out`
- `Episode_Termination/base_contact`
- `Episode_Termination/bad_orientation`
