# 本地 MuJoCo Sim2Sim

[English](README.md)

该目录包含 Cyvet 的本地 MuJoCo sim2sim 回放脚本，可加载 Isaac Lab 训练得到的 `rsl_rl` actor-critic checkpoint。

## 范围

当前脚本用于本地策略回放和基础 sim2sim 检查。

- 机器人：Cyvet
- 策略格式：`rsl_rl` actor-critic checkpoint
- 控制指令：命令行速度指令
- MuJoCo actuator：显式 torque PD

MuJoCo 模型使用 `deploy/sim2sim/assets/cyvet/` 下的 Cyvet XML 资产。脚本启动时会关闭 XML position actuator 的内置增益，并直接施加 PD torque。`control.actuator_model` 中的执行器参数与 Isaac Lab 训练里的 Cyvet actuator 对齐，包括 armature、TN 限幅和摩擦项。

## 运行环境

安装 sim2sim 所需的 Python 依赖：

```bash
python -m pip install -r deploy/sim2sim/requirements.txt
```

## 配置

运行前先在 `deploy/sim2sim/configs/cyvet.yaml` 中设置 checkpoint：

```yaml
policy:
  checkpoint: logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt
```

默认速度指令也在同一个配置中：

```yaml
commands:
  lin_vel_x: 0.5
  lin_vel_y: 0.0
  ang_vel_z: 0.0
```

也可以通过命令行覆盖速度指令。

执行器延迟默认为 0：

```yaml
control:
  delay_steps: 0
```

## 使用

打开 MuJoCo viewer：

```bash
python deploy/sim2sim/play_mujoco.py \
  --config deploy/sim2sim/configs/cyvet.yaml \
  --cmd-vx 0.5 \
  --cmd-vy 0.0 \
  --cmd-yaw 0.0
```

只检查配置：

```bash
python deploy/sim2sim/play_mujoco.py \
  --config deploy/sim2sim/configs/cyvet.yaml \
  --dry-run
```

## 说明

- MuJoCo 的 leg-major 关节顺序会在脚本中转换为策略使用的关节顺序。
- 策略观测为 Isaac Lab 任务中的 45 维 actor observation。
- 当前脚本使用显式 torque PD，并通过配置的 TN 曲线和 `control.torque_limit` 限制扭矩。
- 速度指令来自 YAML 或命令行参数。
- 本地 runner 不经过 Uniubi SDK。SDK 级 sim2sim 见 [../README.zh-CN.md](../README.zh-CN.md)。
