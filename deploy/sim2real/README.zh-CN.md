# Sim2Real

[English](README.md)

该目录用于放置 sim2real 部署说明。

当前公开流程：

1. 从训练好的 checkpoint 导出 `policy.onnx`。
2. 使用本地 MuJoCo sim2sim 验证 checkpoint。
3. 可选：通过 SDK sim2sim 验证 ONNX 策略和低级 SDK 链路。
4. 转换为板端推理格式。

板端部署建议使用 TensorRT engine 进行策略推理。ONNXRuntime 主要用于 x86 仿真验证和 SDK 接口联调。

SDK sim2real 中运行 Python 控制进程时，建议绑定到独立 CPU 核：

```bash
taskset -c 2 python <your_sdk_sim2real_script>.py ...
```

Python SDK 的编译和安装请参考：

[uniubi-ai/uniubi_robot_sdk_py develop](https://github.com/uniubi-ai/uniubi_robot_sdk_py/tree/develop)
