# Deployment

[中文文档](README.zh-CN.md)

Deployment-related documentation is grouped here.

Recommended workflow:

1. Train a policy in Isaac Lab.
2. Export the policy to ONNX.
3. Validate with local MuJoCo sim2sim.
4. Optionally validate through the SDK sim2sim bridge.
5. Prepare sim2real deployment.

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

[uniubi-ai/uniubi_robot_sdk_py develop](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/develop)

## Sim2Real

Sim2Real notes are kept under:

[sim2real/README.md](sim2real/README.md)

For on-board deployment, use a TensorRT engine for policy inference. ONNXRuntime is intended for x86 simulation and integration checks.

For SDK sim2real, binding the Python control process to a dedicated CPU core is recommended:

```bash
taskset -c 2 python <your_sdk_sim2real_script>.py ...
```
