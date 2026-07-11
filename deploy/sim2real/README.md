# Sim2Real

[中文文档](README.zh-CN.md)

This directory is reserved for sim2real deployment notes.

Current public workflow:

1. Export `policy.onnx` from a trained checkpoint.
2. Validate the checkpoint with local MuJoCo sim2sim.
3. Optionally validate the ONNX policy through SDK sim2sim.
4. Convert the deployment model to the board-side inference format.

For on-board deployment, use a TensorRT engine for policy inference. ONNXRuntime is intended for x86 simulation and SDK integration checks.

For SDK sim2real, binding the Python control process to a dedicated CPU core is recommended:

```bash
taskset -c 2 python <your_sdk_sim2real_script>.py ...
```

Python SDK build and installation should follow:

[uniubi-ai/uniubi_robot_sdk_py develop](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/develop)
