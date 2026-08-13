# Sim2Real

[English](README.md)

本文说明如何把本仓公开的 Cyvet locomotion checkpoint 导出为 ONNX，并通过 Uniubi
Low-level SDK 的 TensorRT 示例部署到 JetPack 6.2.1 Orin。训练环境需要 PyTorch；
板端推理只需要 ONNX、TensorRT/CUDA 和 SDK，**不需要安装 PyTorch 或 ONNX Runtime**。

## 1. 导出 ONNX

```bash
python scripts/rsl_rl/play.py \
  --task=Uniubi-Cyvet-Velocity \
  --checkpoint logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt \
  --headless \
  --num_envs=1 \
  --export-only
```

产物位于 checkpoint 同级目录：

```text
logs/rsl_rl/cyvet_velocity/<run>/exported/policy.onnx
logs/rsl_rl/cyvet_velocity/<run>/exported/policy.pt
```

板端 TensorRT 流程输入 `policy.onnx`；`policy.pt` 只用于需要 TorchScript 的开发链路。

## 2. 当前公开 Cyvet 模型契约

以下契约对应 `Uniubi-Cyvet-Velocity` 当前配置和
`deploy/sim2sim/configs/cyvet.yaml`，不能推广到其他 task 或历史 checkpoint。替换模型时
必须重新核对 ONNX shape、observation、归一化、关节顺序、action scale 和控制周期。

ONNX 输入输出：

```text
input:  float32 [1, 45]
output: float32 [1, 12]
```

45 维 actor observation 按以下顺序拼接：

| 范围 | 内容 | 训练侧缩放 |
|---|---|---:|
| `0:3` | base angular velocity | `0.2` |
| `3:6` | projected gravity | `1.0` |
| `6:9` | command `[vx, vy, yaw]` | `1.0` |
| `9:21` | joint position relative to default pose | `1.0` |
| `21:33` | joint velocity | `0.05` |
| `33:45` | previous policy action | `1.0` |

模型的关节输入/输出使用 joint-major 顺序：

```text
FL_ABAD, FR_ABAD, RL_ABAD, RR_ABAD,
FL_HIP,  FR_HIP,  RL_HIP,  RR_HIP,
FL_KNEE, FR_KNEE, RL_KNEE, RR_KNEE
```

默认关节位置为每条腿 `ABAD=0.0, HIP=0.8, KNEE=-1.58` rad，action scale
为 `0.25`。公开参考运行时使用 50 Hz 策略周期、位置 PD `Kp=35, Kd=1`。

## 3. Sim2Sim 验证

先用 [本地 MuJoCo sim2sim](../sim2sim/README.zh-CN.md) 验证指定 checkpoint。需要进一步
验证 Low-level SDK 数据链路时，再使用
[Uniubi Robot Mock SDK Sim2Sim](https://github.com/uniubi-ai/uniubi_robot_mock/blob/main/docs/sim2sim_sdk_zh.md)。

Sim2Sim 通过只能说明模型和接口契约基本一致，不等于实机控制已经安全通过。

## 4. 使用 SDK TensorRT 示例部署

参考实现：

- C++：[`example_lowlevel_tensorrt.cpp`](https://github.com/uniubi-ai/uniubi_robot_sdk/blob/main/examples/example_lowlevel_tensorrt.cpp)
- Python：[`example_lowlevel_tensorrt.py`](https://github.com/uniubi-ai/uniubi_robot_sdk_py/blob/main/examples/example_lowlevel_tensorrt.py)

两套示例都直接输入 ONNX，并在**每次进程启动时**重新构建 TensorRT engine，不读取
或写入 `.engine` 缓存。当前示例使用 FP32；C++ 示例还显式关闭 TF32。C++ 的 Orin
原生编译和 Ubuntu 22.04 x86_64 交叉编译说明见
[Uniubi SDK 构建指南](https://github.com/uniubi-ai/uniubi-docs/blob/main/docs/BUILD.md#31-交叉编译-tensorrt-示例的额外边界)。

### 4.1 板端环境

Uniubi 出厂 Orin 已包含与系统匹配的 JetPack、CUDA 和 TensorRT，不需要重新刷写或
安装 JetPack，也不需要安装 Torch。部署前只核对版本和 C++ 运行库：

```bash
dpkg-query -W nvidia-jetpack libnvinfer10 2>/dev/null || true
test -f /usr/local/cuda/include/cuda_runtime_api.h
test -f /usr/include/aarch64-linux-gnu/NvInfer.h
```

当前参考目标是 JetPack 6.2.1、CUDA 12.6、TensorRT 10.3。如果目标机版本不同，必须
重新验证编译 ABI 和 TensorRT API，不能直接复用本流程的二进制。

### 4.2 部署产物

C++ 路径至少部署以下内容，且 SDK 头文件、示例二进制和 `lib/aarch64/` 必须来自同一
SDK 提交：

```text
uniubi_cyvet_deploy/
├── bin/example_lowlevel_tensorrt
├── lib/                         # uniubi_robot_sdk/lib/aarch64/
└── models/policy.onnx
```

在编译机上示例：

```bash
export ROBOT=uniubi@ROBOT_IP
export DEPLOY_ROOT=/home/uniubi/uniubi_cyvet_deploy
export POLICY_ONNX=/path/to/exported/policy.onnx

ssh "$ROBOT" "mkdir -p '$DEPLOY_ROOT/bin' '$DEPLOY_ROOT/lib' '$DEPLOY_ROOT/models'"
scp build-aarch64/examples/example_lowlevel_tensorrt \
  "$ROBOT:$DEPLOY_ROOT/bin/"
rsync -a lib/aarch64/ "$ROBOT:$DEPLOY_ROOT/lib/"
scp "$POLICY_ONNX" \
  "$ROBOT:$DEPLOY_ROOT/models/"
```

登录 Orin 后先检查架构和动态库，不要在存在 `not found` 时启动控制：

```bash
export DEPLOY_ROOT=/home/uniubi/uniubi_cyvet_deploy
export LD_LIBRARY_PATH="$DEPLOY_ROOT/lib:/vendor/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

file "$DEPLOY_ROOT/bin/example_lowlevel_tensorrt"
ldd "$DEPLOY_ROOT/bin/example_lowlevel_tensorrt"
```

Python 路径部署同一个 `policy.onnx`，并按
[`uniubi_robot_sdk_py` README](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/main)
安装 SDK 和示例；不要为 TensorRT 推理额外安装 PyTorch。

### 4.3 模型验证与启动

先执行纯模型验证；该模式不初始化 SDK，也不连接或使能机器人：

```bash
taskset -c 2 "$DEPLOY_ROOT/bin/example_lowlevel_tensorrt" \
  --onnx "$DEPLOY_ROOT/models/policy.onnx" --validate-only
```

实机启动示例：

```bash
sudo env LD_LIBRARY_PATH="$LD_LIBRARY_PATH" \
  taskset -c 2 "$DEPLOY_ROOT/bin/example_lowlevel_tensorrt" \
  --onnx "$DEPLOY_ROOT/models/policy.onnx"
```

绑定 CPU 2 可以减少调度抖动，使观测获取耗时和 50 Hz 控制周期更稳定；如果设备已有
不同的 CPU 隔离方案，应使用实际分配给控制进程的独立核心。

## 5. SDK 顺序与使能门槛

当前机器人 `MotorLayout` 应返回 12 个关节，SDK 使用 leg-major 顺序：

```text
FL_ABAD, FL_HIP, FL_KNEE,
FR_ABAD, FR_HIP, FR_KNEE,
RL_ABAD, RL_HIP, RL_KNEE,
RR_ABAD, RR_HIP, RR_KNEE
```

部署程序必须在 `kConnected` 后调用 `getMotorLayout()`，校验数量和实际
`(limbNo, jointNo)` 顺序，再按返回的 `limbNo` / `jointNo` 构造控制帧。不得直接把
模型数组下标当作 SDK 电机下标。

参考示例显式执行：

```text
SDK leg-major -> 模型 joint-major -> SDK leg-major
```

以下任一条件不满足时必须在 `setMotionEnable(true)` 前拒绝控制：

1. MotorLayout 不是预期的 12 关节 leg-major 布局；
2. ONNX 不是 float32 `[1,45] -> [1,12]`；
3. observation、模型关节顺序或 action contract 与上文不一致。

## 6. 实机验证与退出

首次验证必须把机器狗可靠放在安全吊架上，保持四脚腾空、急停可触达并有人值守：

```text
lowlevel> stand
lowlevel> walk 0.5 0 0
lowlevel> stop
lowlevel> lay
lowlevel> quit
```

TensorRT 策略示例退出时只在 prepared 状态调用 `setMotionEnable(false)`，随后断开连接
并关闭 SDK；不会调用 `emergencyStop()` 或 `restoreMotionControlMode()`。

Python SDK 的安装见
[`uniubi_robot_sdk_py`](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/main)，完整
Low-level API 和安全边界见
[`uniubi_low_level_sdk.md`](https://github.com/uniubi-ai/uniubi-docs/blob/main/docs/uniubi_low_level_sdk.md)。
