# Uniubi RL Lab

[English](README.md)

Uniubi RL Lab 是 Uniubi 机器人的仿真训练项目，目前包括 Cyvet 四足机器人。

## 概览

<p align="center">
  <img src="docs/media/cyvet_isaaclab.gif" width="640" alt="Cyvet 四足机器人在 Isaac Lab 中运行">
</p>

当前任务：

```text
Uniubi-Cyvet-Velocity
```

## 功能

当前仓库包含：

- Cyvet USD 机器人资产加载。
- Uniubi 显式执行器模型和 Cyvet 执行器参数。
- 基于 Isaac Lab manager-based 环境的速度跟踪任务。
- 基于 RSL-RL PPO 的 MLP actor-critic 配置。
- 训练、回放、零动作、随机动作和任务列表脚本。
- 策略导出、本地 MuJoCo sim2sim、SDK sim2sim 和 sim2real 部署文档。

## 版本

当前开发和验证使用：

- Python 3.11
- Isaac Sim 5.1
- Isaac Lab 2.3.2
- PyTorch 2.7.0 CUDA 12.8
- RSL-RL 3.0.1 或更新版本

## 安装

先创建并激活 Python 环境：

```bash
conda create -n env_isaaclab_5.1 python=3.11 -y
conda activate env_isaaclab_5.1
```

按照 Isaac Lab 官方文档安装 Isaac Sim、Isaac Lab 和相关依赖：

[Isaac Lab 2.3.2 pip installation](https://isaac-sim.github.io/IsaacLab/v2.3.2/source/setup/installation/pip_installation.html)

安装好 Isaac Lab 后，在当前仓库根目录执行 editable 安装：

```bash
cd /path/to/uniubi_rl_lab
python -m pip install -e source/uniubi_rl_lab
```

第一次启动 Isaac Sim 时，NVIDIA Omniverse 可能会要求接受 EULA。请在交互式终端中执行：

```bash
python -c "import isaacsim"
```

根据提示输入 `Yes`。

## 验证安装

查看已注册的 Uniubi 任务：

```bash
python scripts/list_envs.py
```

运行一次最小训练验证：

```bash
python scripts/rsl_rl/train.py \
  --task=Uniubi-Cyvet-Velocity \
  --headless \
  --num_envs=16 \
  --max_iterations=1 \
  --device cuda:0
```

正常情况下，环境摘要中应包含：

```text
Physics step-size     : 0.004
Environment step-size : 0.02
Active Action Terms (shape: 12)
policy observation shape: 45
critic observation shape: 60
```

## 训练

启动完整 PPO 训练：

```bash
python scripts/rsl_rl/train.py \
  --task=Uniubi-Cyvet-Velocity \
  --headless \
  --device cuda:0 \
  --run_name cyvet_velocity
```

调试时可以减小环境数量和迭代次数：

```bash
python scripts/rsl_rl/train.py \
  --task=Uniubi-Cyvet-Velocity \
  --headless \
  --device cuda:0 \
  --num_envs=1024 \
  --max_iterations=1000 \
  --run_name debug
```

训练日志会写入：

```text
logs/rsl_rl/cyvet_velocity/<timestamp>_<run_name>/
```

每个 run 会保存：

- `params/env.yaml`
- `params/agent.yaml`
- TensorBoard event 文件
- `model_*.pt` checkpoint
- `isaaclab/` 运行日志
- `git/` 代码 diff 快照

## 回放

`play.py` 默认使用 `quality` 渲染，并从完整回放速度范围中采样速度指令。

运行训练得到的 checkpoint：

```bash
python scripts/rsl_rl/play.py \
  --task=Uniubi-Cyvet-Velocity \
  --checkpoint logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt \
  --num_envs=32
```

无界面回放：

```bash
python scripts/rsl_rl/play.py \
  --task=Uniubi-Cyvet-Velocity \
  --checkpoint logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt \
  --num_envs=32 \
  --headless
```

## 部署

部署相关文档统一放在：

[deploy/README.zh-CN.md](deploy/README.zh-CN.md)

当前包含：

- 从训练 checkpoint 导出 ONNX。
- Cyvet 本地 MuJoCo sim2sim 回放。
- 可选：通过 `uniubi_robot_mock` 进行 SDK sim2sim。
- Sim2Real 说明。

## 调试脚本

零动作和随机动作脚本可以用来检查 reset、step、动作维度和 contact 配置：

```bash
python scripts/zero_agent.py --task=Uniubi-Cyvet-Velocity --num_envs=16 --headless
python scripts/random_agent.py --task=Uniubi-Cyvet-Velocity --num_envs=16 --headless
```

## 任务说明

Cyvet 资产、执行器、观测、奖励和控制频率见：

[docs/cyvet_locomotion.zh-CN.md](docs/cyvet_locomotion.zh-CN.md)

## 许可证

本仓库中的 Uniubi 原创源码使用 Apache License 2.0。
源自或改编自 Isaac Lab 的文件继续保留 BSD-3-Clause 声明。
带有独立 SPDX 标识、版权头或许可证声明的文件继续遵循其原有条款。
详见 [LICENSE](LICENSE)、[NOTICE](NOTICE) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 目录结构

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
  README.zh-CN.md
  sim2sim/play_mujoco.py
  sim2sim/configs/cyvet.yaml
  sim2real/README.zh-CN.md
```

## 常见问题

如果训练报 `/tmp/isaaclab/logs` 权限错误，请确认使用的是本仓库中的 `scripts/rsl_rl/train.py`。该脚本会把 Isaac Lab 运行日志写入当前 run 目录。

如果进程在任务初始化前停在 Omniverse EULA 提示，请执行：

```bash
python -c "import isaacsim"
```

并在交互式终端中接受 EULA。

如果任务找不到，请重新安装扩展：

```bash
python -m pip install -e source/uniubi_rl_lab
python scripts/list_envs.py
```
