# Sim2Real

[简体中文](README.zh-CN.md)

This guide exports the public Cyvet locomotion checkpoint to ONNX and deploys it
through the Uniubi Low-level SDK TensorRT examples on a JetPack 6.2.1 Orin.
Training requires PyTorch; on-board inference requires only ONNX, TensorRT/CUDA,
and the SDK. **PyTorch and ONNX Runtime are not required on the robot.**

## 1. Export ONNX

```bash
python scripts/rsl_rl/play.py \
  --task=Uniubi-Cyvet-Velocity \
  --checkpoint logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt \
  --headless \
  --num_envs=1 \
  --export-only
```

The files are written next to the checkpoint:

```text
logs/rsl_rl/cyvet_velocity/<run>/exported/policy.onnx
logs/rsl_rl/cyvet_velocity/<run>/exported/policy.pt
```

The on-board TensorRT path consumes `policy.onnx`. `policy.pt` is only for
development paths that explicitly use TorchScript.

## 2. Current public Cyvet model contract

This contract belongs to the current `Uniubi-Cyvet-Velocity` task and
`deploy/sim2sim/configs/cyvet.yaml`. Do not assume that it applies to another
task or an older checkpoint. Revalidate the ONNX shapes, observation,
normalization, joint order, action scale, and control rate whenever the model
changes.

```text
input:  float32 [1, 45]
output: float32 [1, 12]
```

The 45-element actor observation is concatenated as follows:

| Range | Value | Training scale |
|---|---|---:|
| `0:3` | base angular velocity | `0.2` |
| `3:6` | projected gravity | `1.0` |
| `6:9` | command `[vx, vy, yaw]` | `1.0` |
| `9:21` | joint position relative to the default pose | `1.0` |
| `21:33` | joint velocity | `0.05` |
| `33:45` | previous policy action | `1.0` |

Model joint inputs and outputs use joint-major order:

```text
FL_ABAD, FR_ABAD, RL_ABAD, RR_ABAD,
FL_HIP,  FR_HIP,  RL_HIP,  RR_HIP,
FL_KNEE, FR_KNEE, RL_KNEE, RR_KNEE
```

The default pose is `ABAD=0.0, HIP=0.8, KNEE=-1.58` rad on every leg, and the
action scale is `0.25`. The public reference runtime uses a 50 Hz policy rate
and position PD gains `Kp=35, Kd=1`.

## 3. Validate in Sim2Sim

First validate the exact checkpoint with the
[local MuJoCo sim2sim](../sim2sim/README.md). To additionally validate the
Low-level SDK transport, use the
[Uniubi Robot Mock SDK Sim2Sim](https://github.com/uniubi-ai/uniubi_robot_mock/blob/main/docs/sim2sim_sdk.md).

Passing Sim2Sim checks the model and interface contract; it does not establish
that real-robot control is safe.

## 4. Deploy with an SDK TensorRT example

Reference implementations:

- C++: [`example_lowlevel_tensorrt.cpp`](https://github.com/uniubi-ai/uniubi_robot_sdk/blob/main/examples/example_lowlevel_tensorrt.cpp)
- Python: [`example_lowlevel_tensorrt.py`](https://github.com/uniubi-ai/uniubi_robot_sdk_py/blob/main/examples/example_lowlevel_tensorrt.py)

Both examples take ONNX as input and rebuild a TensorRT engine at **every
process startup**; they do not read or write an `.engine` cache. The current
examples use FP32, and the C++ example explicitly disables TF32. Native Orin
and Ubuntu 22.04 x86_64 cross-build instructions are in the
[Uniubi SDK build guide](https://github.com/uniubi-ai/uniubi-docs/blob/main/docs/BUILD.md#31-additional-requirements-for-the-tensorrt-example).

### 4.1 Board environment

Uniubi factory Orin images already contain the matching JetPack, CUDA, and
TensorRT stack. Do not reflash or reinstall JetPack, and do not install Torch
for this deployment path. Check the versions and C++ development files first:

```bash
dpkg-query -W nvidia-jetpack libnvinfer10 2>/dev/null || true
test -f /usr/local/cuda/include/cuda_runtime_api.h
test -f /usr/include/aarch64-linux-gnu/NvInfer.h
```

The current reference target is JetPack 6.2.1, CUDA 12.6, and TensorRT 10.3.
If the target differs, revalidate the compiler ABI and TensorRT API instead of
reusing the binary from this workflow.

### 4.2 Deploy artifacts

For the C++ path, deploy at least the following files. The SDK headers, example
binary, and `lib/aarch64/` must come from the same SDK commit:

```text
uniubi_cyvet_deploy/
├── bin/example_lowlevel_tensorrt
├── lib/                         # uniubi_robot_sdk/lib/aarch64/
└── models/policy.onnx
```

Example commands on the build host:

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

On the Orin, check the architecture and dynamic libraries before starting any
control process. Do not continue if `ldd` reports `not found`:

```bash
export DEPLOY_ROOT=/home/uniubi/uniubi_cyvet_deploy
export LD_LIBRARY_PATH="$DEPLOY_ROOT/lib:/vendor/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

file "$DEPLOY_ROOT/bin/example_lowlevel_tensorrt"
ldd "$DEPLOY_ROOT/bin/example_lowlevel_tensorrt"
```

For the Python path, deploy the same `policy.onnx` and install the SDK and
example as described in the
[`uniubi_robot_sdk_py` README](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/main).
Do not install PyTorch solely for TensorRT inference.

### 4.3 Model validation and startup

Validate the model first. This mode does not initialize the SDK or connect to
or enable the robot:

```bash
taskset -c 2 "$DEPLOY_ROOT/bin/example_lowlevel_tensorrt" \
  --onnx "$DEPLOY_ROOT/models/policy.onnx" --validate-only
```

Start the real-robot process with root privileges:

```bash
sudo env LD_LIBRARY_PATH="$LD_LIBRARY_PATH" \
  taskset -c 2 "$DEPLOY_ROOT/bin/example_lowlevel_tensorrt" \
  --onnx "$DEPLOY_ROOT/models/policy.onnx"
```

Binding CPU 2 reduces scheduling jitter and stabilizes observation acquisition
and the 50 Hz control period. If the target has a different CPU isolation plan,
use the dedicated core assigned to the control process.

## 5. SDK order and enable gate

The current robot `MotorLayout` contains 12 joints in SDK leg-major order:

```text
FL_ABAD, FL_HIP, FL_KNEE,
FR_ABAD, FR_HIP, FR_KNEE,
RL_ABAD, RL_HIP, RL_KNEE,
RR_ABAD, RR_HIP, RR_KNEE
```

After reaching `kConnected`, the deployment process must call
`getMotorLayout()`, validate the count and actual `(limbNo, jointNo)` order,
and construct control frames with the returned `limbNo` and `jointNo`. Never
treat a model array index as an SDK motor index.

The reference examples explicitly perform:

```text
SDK leg-major -> model joint-major -> SDK leg-major
```

Control must be rejected before `setMotionEnable(true)` if any of these checks
fails:

1. MotorLayout is not the expected 12-joint leg-major layout.
2. ONNX is not float32 `[1,45] -> [1,12]`.
3. The observation, model joint order, or action contract differs from this guide.

## 6. Real-robot validation and shutdown

For the first test, secure the robot on a safety rig with all feet clear, keep
the emergency stop reachable, and have an operator present. Validate only
standing and laying on the rig; do not validate walking while suspended:

```text
lowlevel> stand
lowlevel> lay
lowlevel> quit
```

After `stand` and `lay` confirm the expected motion and joint directions, move
the robot off the rig onto clear, level, obstacle-free ground. Keep the
emergency stop reachable and an operator present, then validate walking:

```text
lowlevel> stand
lowlevel> walk 0.5 0 0
lowlevel> stop
lowlevel> lay
lowlevel> quit
```

On exit, the TensorRT policy examples call `setMotionEnable(false)` only from
the prepared state, then disconnect and shut down the SDK. They do not call
`emergencyStop()` or `restoreMotionControlMode()`.

For Python SDK installation, see
[`uniubi_robot_sdk_py`](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/main).
For the full Low-level API and safety boundaries, see
[`uniubi_low_level_sdk.md`](https://github.com/uniubi-ai/uniubi-docs/blob/main/docs/uniubi_low_level_sdk.md).
