# 部署

[English](README.md)

部署相关文档统一放在这里。

## 推荐流程

1. 在 Isaac Lab 中训练策略。
2. 从明确的 checkpoint 导出 ONNX，并记录 task、checkpoint 路径和模型契约。
3. 用本地 MuJoCo sim2sim 验证同一个 checkpoint。
4. 可选：通过 SDK sim2sim bridge 验证 Low-level SDK 链路和关节重排。
5. 在板端先执行 TensorRT `--validate-only`；吊架上只验证 `stand` 和 `lay`，确认正常
   后再放到空旷平整地面验证 `walk`。

每一步都必须使用同一份模型契约；不能只替换 ONNX 文件而沿用未经核对的 observation、
归一化、关节顺序、action scale 或控制周期。

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

[uniubi-ai/uniubi_robot_sdk_py main](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/main)

## Sim2Real

完整板端部署说明：

[sim2real/README.zh-CN.md](sim2real/README.zh-CN.md)

当前公开 Cyvet 策略是 float32 `[1,45] -> [1,12]`。模型使用 joint-major 关节顺序，
SDK/机器人 `MotorLayout` 使用 leg-major 顺序；板端程序必须通过 `getMotorLayout()`
校验实际布局，并显式完成双向重排，不能依赖硬编码 SDK 数组下标。

板端推荐直接输入 ONNX，由 C++ 或 Python SDK TensorRT 示例在每次启动时重新构建
FP32 engine。板端不需要 PyTorch 或 ONNX Runtime。参考实现：

- [C++ Low-level TensorRT 示例](https://github.com/uniubi-ai/uniubi_robot_sdk/blob/main/examples/example_lowlevel_tensorrt.cpp)
- [Python Low-level TensorRT 示例](https://github.com/uniubi-ai/uniubi_robot_sdk_py/blob/main/examples/example_lowlevel_tensorrt.py)

先做不连接机器人的模型验证：

```bash
taskset -c 2 ./example_lowlevel_tensorrt \
  --onnx /path/to/policy.onnx --validate-only
```

实机控制进程建议继续通过 `taskset -c 2` 绑定 CPU 2，以减少调度抖动。只有模型 shape、
observation、模型关节顺序、MotorLayout 和 action contract 全部匹配后，才允许使能
Low-level 控制。
