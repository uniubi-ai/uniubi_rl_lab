# 部署

[English](README.md)

部署相关文档统一放在这里。

推荐流程：

1. 在 Isaac Lab 中训练策略。
2. 导出 ONNX。
3. 先用本地 MuJoCo sim2sim 验证。
4. 可选：通过 SDK sim2sim bridge 验证低级 SDK 链路。
5. 准备 sim2real 部署。

## 导出 ONNX

`scripts/rsl_rl/play.py` 会在回放前导出 JIT 和 ONNX 策略。使用 `--export-only` 可以只导出并退出：

```bash
python scripts/rsl_rl/play.py \
  --task=Uniubi-Cyvet-Velocity \
  --checkpoint logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt \
  --headless \
  --num_envs=1 \
  --export-only
```

导出文件会写到 checkpoint 同级目录：

```text
logs/rsl_rl/cyvet_velocity/<run>/exported/policy.onnx
logs/rsl_rl/cyvet_velocity/<run>/exported/policy.pt
```

## 本地 Sim2Sim

不经过 Uniubi SDK 的快速 MuJoCo 回放见：

[sim2sim/README.zh-CN.md](sim2sim/README.zh-CN.md)

## 可选：SDK Sim2Sim

如果要验证 SDK 低级控制链路，参考 Uniubi Robot Mock 的 SDK sim2sim 文档：

[uniubi-ai/uniubi_robot_mock docs/sim2sim_sdk_zh.md](https://github.com/uniubi-ai/uniubi_robot_mock/blob/main/docs/sim2sim_sdk_zh.md)

这条链路会启动 MuJoCo bridge，并通过 DDS topic 交换低级控制和机器人 observed 状态。使用本仓导出的 `policy.onnx` 作为 mock 侧 policy client 的 ONNX 模型输入。

如果需要编译或安装 SDK sim2sim client 使用的 Python SDK，请参考：

[uniubi-ai/uniubi_robot_sdk_py develop](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/develop)

## Sim2Real

Sim2Real 说明放在：

[sim2real/README.zh-CN.md](sim2real/README.zh-CN.md)

板端部署建议使用 TensorRT engine 进行策略推理。ONNXRuntime 主要用于 x86 仿真验证和接口联调。

SDK sim2real 中运行 Python 控制进程时，建议绑定到独立 CPU 核：

```bash
taskset -c 2 python <your_sdk_sim2real_script>.py ...
```
