# Deployment

[中文文档](README.zh-CN.md)

Deployment-related documentation is grouped here.

## Recommended workflow

1. Train a policy in Isaac Lab.
2. Export ONNX from an identified checkpoint and record the task, checkpoint
   path, and model contract.
3. Validate the same checkpoint with local MuJoCo sim2sim.
4. Optionally validate the Low-level SDK transport and joint reorder through
   the SDK sim2sim bridge.
5. Run TensorRT `--validate-only` on the board. Validate only `stand` and `lay`
   on a safety rig, then move to clear, level ground to validate `walk`.

Every stage must use the same model contract. Do not replace only the ONNX file
while reusing an unverified observation, normalization, joint order, action
scale, or control rate.

## Export ONNX

`scripts/rsl_rl/play.py` exports both JIT and ONNX policies before running playback. Use `--export-only` to export and exit:

```bash
python scripts/rsl_rl/play.py \
  --task=Uniubi-Cyvet-Velocity \
  --checkpoint logs/rsl_rl/cyvet_velocity/<run>/model_<iter>.pt \
  --headless \
  --num_envs=1 \
  --export-only
```

The exported files are written next to the checkpoint:

```text
logs/rsl_rl/cyvet_velocity/<run>/exported/policy.onnx
logs/rsl_rl/cyvet_velocity/<run>/exported/policy.pt
```

## Local Sim2Sim

Use the local MuJoCo runner for quick policy playback without the Uniubi SDK:

[sim2sim/README.md](sim2sim/README.md)

## Optional SDK Sim2Sim

For SDK-level sim2sim, follow the Uniubi Robot Mock SDK sim2sim guide:

[uniubi-ai/uniubi_robot_mock docs/sim2sim_sdk.md](https://github.com/uniubi-ai/uniubi_robot_mock/blob/main/docs/sim2sim_sdk.md)

That workflow runs a MuJoCo bridge that exchanges low-level control and observed state through DDS topics. Use the exported `policy.onnx` as the ONNX model input for the mock-side policy client.

If you need to build or install the Python SDK used by the SDK sim2sim client, refer to:

[uniubi-ai/uniubi_robot_sdk_py main](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/main)

## Sim2Real

Full on-board deployment guide:

[sim2real/README.md](sim2real/README.md)

The current public Cyvet policy is float32 `[1,45] -> [1,12]`. The model uses
joint-major order while the robot SDK `MotorLayout` uses leg-major order. The
deployment process must validate the actual layout with `getMotorLayout()` and
perform both reorders explicitly; it must not rely on hard-coded SDK array
indices.

On the board, pass ONNX directly to a C++ or Python SDK TensorRT example. Both
rebuild an FP32 engine at every process startup. PyTorch and ONNX Runtime are not
required on the robot. Reference implementations:

- [C++ Low-level TensorRT example](https://github.com/uniubi-ai/uniubi_robot_sdk/blob/main/examples/example_lowlevel_tensorrt.cpp)
- [Python Low-level TensorRT example](https://github.com/uniubi-ai/uniubi_robot_sdk_py/blob/main/examples/example_lowlevel_tensorrt.py)

Run model-only validation first:

```bash
taskset -c 2 ./example_lowlevel_tensorrt \
  --onnx /path/to/policy.onnx --validate-only
```

Continue to bind the real-robot control process to CPU 2 with `taskset -c 2` to
reduce scheduling jitter. Low-level control may be enabled only after the model
shape, observation, model joint order, MotorLayout, and action contract all
match.
