#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run a trained Cyvet policy in a local MuJoCo simulation."""

from __future__ import annotations

import argparse
import inspect
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

LEG_MAJOR_TO_PER_JOINT = np.asarray([0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11], dtype=np.int64)
PER_JOINT_TO_LEG_MAJOR = np.asarray([0, 4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11], dtype=np.int64)


class RslRlPolicyAdapter(torch.nn.Module):
    """Keep this runner's tensor-only inference path compatible with RSL-RL 3.x."""

    def __init__(self, policy: torch.nn.Module, policy_obs_key: str | None = None):
        super().__init__()
        self.policy = policy
        self.policy_obs_key = policy_obs_key

    def act_inference(self, obs: torch.Tensor) -> torch.Tensor:
        if self.policy_obs_key is None:
            return self.policy.act_inference(obs)
        try:
            from tensordict import TensorDict
        except ImportError as exc:
            raise ImportError("RSL-RL 3.x inference requires tensordict. Install deploy/sim2sim/requirements.txt.") from exc
        obs_dict = TensorDict({self.policy_obs_key: obs}, batch_size=obs.shape[:-1])
        return self.policy.act_inference(obs_dict)


def make_rsl_rl_actor_critic(ActorCritic, policy_cfg: dict[str, Any]) -> tuple[torch.nn.Module, str | None]:
    kwargs = {
        "num_actions": int(policy_cfg["num_actions"]),
        "actor_hidden_dims": list(policy_cfg["actor_hidden_dims"]),
        "critic_hidden_dims": list(policy_cfg["critic_hidden_dims"]),
        "activation": policy_cfg.get("activation", "elu"),
        "init_noise_std": float(policy_cfg.get("init_noise_std", 1.0)),
    }
    signature = inspect.signature(ActorCritic)
    if "obs" not in signature.parameters:
        return (
            ActorCritic(
                num_actor_obs=int(policy_cfg["num_actor_obs"]),
                num_critic_obs=int(policy_cfg["num_critic_obs"]),
                **kwargs,
            ),
            None,
        )

    try:
        from tensordict import TensorDict
    except ImportError as exc:
        raise ImportError("RSL-RL 3.x requires tensordict. Install deploy/sim2sim/requirements.txt.") from exc

    policy_key = "policy"
    critic_key = "critic"
    obs = TensorDict(
        {
            policy_key: torch.zeros(1, int(policy_cfg["num_actor_obs"])),
            critic_key: torch.zeros(1, int(policy_cfg["num_critic_obs"])),
        },
        batch_size=[1],
    )
    policy = ActorCritic(
        obs=obs,
        obs_groups={"policy": [policy_key], "critic": [critic_key]},
        **kwargs,
    )
    return policy, policy_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Uniubi Cyvet policy in MuJoCo.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("deploy/sim2sim/configs/cyvet.yaml"),
        help="Path to config YAML.",
    )
    parser.add_argument("--cmd-vx", type=float, default=None, help="Override commanded forward velocity.")
    parser.add_argument("--cmd-vy", type=float, default=None, help="Override commanded lateral velocity.")
    parser.add_argument("--cmd-yaw", type=float, default=None, help="Override commanded yaw velocity.")
    parser.add_argument("--duration", type=float, default=None, help="Override simulation duration in seconds.")
    parser.add_argument("--headless", action="store_true", help="Run without the MuJoCo viewer.")
    parser.add_argument("--real-time", action="store_true", help="Throttle headless simulation to real time.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and exit without importing MuJoCo.")
    parser.add_argument("--device", default="cpu", help="Torch device for policy inference.")
    parser.add_argument("--print-rate", type=float, default=1.0, help="Status print rate in seconds. Use 0 to disable.")
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def mujoco_joint_names_from_cfg(cfg: dict[str, Any]) -> list[str]:
    joint_mapping = cfg["joint_mapping"]
    if "mujoco_joint_names_leg_major" in joint_mapping:
        return joint_mapping["mujoco_joint_names_leg_major"]
    return joint_mapping["mujoco_joint_names"]


def resolve_path(path_text: str, config_path: Path) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute() or path.exists():
        return path
    candidate = (config_path.parent / path).resolve()
    if candidate.exists():
        return candidate
    return path


def load_policy(checkpoint_path: Path, policy_cfg: dict[str, Any], device: str) -> torch.nn.Module:
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint does not exist: {checkpoint_path}")
    if policy_cfg.get("backend", "rsl_rl") != "rsl_rl":
        raise ValueError(f"Unsupported policy backend: {policy_cfg.get('backend')}")

    try:
        from rsl_rl.modules import ActorCritic
    except ImportError as exc:
        raise ImportError(
            "The MuJoCo sim2sim runner expects rsl_rl and its Python dependencies to be installed in the current "
            "environment. Run it from the same environment used for Isaac Lab training."
        ) from exc

    try:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location=device)
    state_dict = checkpoint.get("model_state_dict", checkpoint)
    policy, policy_obs_key = make_rsl_rl_actor_critic(ActorCritic, policy_cfg)
    policy.load_state_dict(state_dict)
    policy.to(device)
    policy.eval()
    return RslRlPolicyAdapter(policy, policy_obs_key)


def quat_apply_inverse(quat_wxyz: np.ndarray, vec: np.ndarray) -> np.ndarray:
    """Match Isaac Lab's quat_apply_inverse(q, v), with q in wxyz order."""
    norm = np.linalg.norm(quat_wxyz)
    if norm > 1.0e-6:
        quat_wxyz = quat_wxyz / norm
    xyz = quat_wxyz[1:]
    t = 2.0 * np.cross(xyz, vec)
    return vec - quat_wxyz[0] * t + np.cross(xyz, t)


def joint_kind(policy_joint_name: str) -> str:
    if "ABAD" in policy_joint_name:
        return "abad"
    if "KNEE" in policy_joint_name:
        return "knee"
    return "hip"


def mujoco_joint_kind(mujoco_joint_name: str) -> str:
    if mujoco_joint_name.endswith("_hip_joint"):
        return "abad"
    if mujoco_joint_name.endswith("_calf_joint"):
        return "knee"
    return "hip"


def command_from_config(cfg: dict[str, Any], args: argparse.Namespace) -> np.ndarray:
    commands = cfg["commands"]
    vx = commands["lin_vel_x"] if args.cmd_vx is None else args.cmd_vx
    vy = commands["lin_vel_y"] if args.cmd_vy is None else args.cmd_vy
    yaw = commands["ang_vel_z"] if args.cmd_yaw is None else args.cmd_yaw
    return np.array([vx, vy, yaw], dtype=np.float32)


def validate_config(cfg: dict[str, Any], config_path: Path) -> None:
    robot_xml = resolve_path(cfg["robot"]["xml_path"], config_path)
    bare_xml = resolve_path(cfg["robot"]["robot_xml_path"], config_path)
    checkpoint = cfg["policy"].get("checkpoint", "")
    policy_joints = cfg["joint_mapping"]["policy_joint_names"]
    mujoco_joints = mujoco_joint_names_from_cfg(cfg)
    if len(policy_joints) != len(mujoco_joints):
        raise ValueError("policy_joint_names and mujoco_joint_names must have the same length.")
    if len(policy_joints) != 12:
        raise ValueError(f"Expected 12 controlled joints, got {len(policy_joints)}.")
    if not robot_xml.exists():
        raise FileNotFoundError(f"MuJoCo scene XML does not exist: {robot_xml}")
    if not bare_xml.exists():
        raise FileNotFoundError(f"MuJoCo robot XML does not exist: {bare_xml}")
    if checkpoint:
        ckpt_path = resolve_path(checkpoint, config_path)
        if not ckpt_path.exists():
            raise FileNotFoundError(f"Configured checkpoint does not exist: {ckpt_path}")


def resolve_sensor_slice(model: Any, mujoco: Any, name: str, expected_dim: int) -> slice | None:
    sensor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, name)
    if sensor_id < 0:
        return None
    sensor_slice = slice(int(model.sensor_adr[sensor_id]), int(model.sensor_adr[sensor_id] + model.sensor_dim[sensor_id]))
    if sensor_slice.stop - sensor_slice.start != expected_dim:
        raise RuntimeError(f"Sensor '{name}' has dim {sensor_slice.stop - sensor_slice.start}, expected {expected_dim}.")
    return sensor_slice


def make_observation(
    data: Any,
    sensor_slices: dict[str, slice | None],
    qpos_addrs_leg_major: list[int],
    qvel_addrs_leg_major: list[int],
    default_joint_pos_model: np.ndarray,
    command: np.ndarray,
    last_action_model: np.ndarray,
    clip_observations: float,
) -> np.ndarray:
    joint_pos_leg = np.array([data.qpos[addr] for addr in qpos_addrs_leg_major], dtype=np.float32)
    joint_vel_leg = np.array([data.qvel[addr] for addr in qvel_addrs_leg_major], dtype=np.float32)
    joint_pos_model = joint_pos_leg[LEG_MAJOR_TO_PER_JOINT]
    joint_vel_model = joint_vel_leg[LEG_MAJOR_TO_PER_JOINT]

    gyro_slice = sensor_slices.get("gyro")
    orientation_slice = sensor_slices.get("orientation")
    if gyro_slice is None:
        base_ang_vel = np.array(data.qvel[3:6], dtype=np.float32)
    else:
        base_ang_vel = np.array(data.sensordata[gyro_slice], dtype=np.float32)
    if orientation_slice is None:
        base_quat = np.array(data.qpos[3:7], dtype=np.float64)
    else:
        base_quat = np.array(data.sensordata[orientation_slice], dtype=np.float64)
    projected_gravity = quat_apply_inverse(base_quat, np.array([0.0, 0.0, -1.0], dtype=np.float64)).astype(np.float32)

    obs = np.concatenate(
        [
            base_ang_vel * 0.2,
            projected_gravity,
            command,
            joint_pos_model - default_joint_pos_model,
            joint_vel_model * 0.05,
            last_action_model,
        ]
    ).astype(np.float32)
    return np.clip(obs, -clip_observations, clip_observations)


def set_initial_state(
    data: Any,
    qpos_addrs_leg_major: list[int],
    qvel_addrs_leg_major: list[int],
    default_joint_pos_leg_major: np.ndarray,
    cfg: dict[str, Any],
) -> None:
    data.qpos[:3] = np.asarray(cfg["robot"].get("initial_base_pos", [0.0, 0.0, 0.42]), dtype=np.float64)
    data.qpos[3:7] = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    for addr, value in zip(qpos_addrs_leg_major, default_joint_pos_leg_major):
        data.qpos[addr] = value
    for addr in qvel_addrs_leg_major:
        data.qvel[addr] = 0.0


def resolve_actuator_ids(model: Any, mujoco: Any, joint_ids: list[int]) -> list[int]:
    actuator_ids = []
    for joint_id in joint_ids:
        for actuator_id in range(model.nu):
            if int(model.actuator_trnid[actuator_id, 0]) == joint_id:
                actuator_ids.append(actuator_id)
                break
        else:
            joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            raise RuntimeError(f"No actuator found for joint: {joint_name}")
    return actuator_ids


def control_values_by_joint_kind(
    cfg: dict[str, Any], joint_names_leg_major: list[str], name: str, default: float
) -> np.ndarray:
    value = cfg.get(name, default)
    if isinstance(value, dict):
        return np.asarray([float(value.get(mujoco_joint_kind(joint_name), default)) for joint_name in joint_names_leg_major])
    return np.full(len(joint_names_leg_major), float(value), dtype=np.float32)


def actuator_model_values(
    cfg: dict[str, Any], joint_names_leg_major: list[str], name: str, default: float
) -> np.ndarray:
    actuator_cfg = cfg["control"].get("actuator_model", {})
    return control_values_by_joint_kind(actuator_cfg, joint_names_leg_major, name, default).astype(np.float32)


def configure_model(
    model: Any,
    cfg: dict[str, Any],
    joint_names_leg_major: list[str],
    joint_ids: list[int],
    actuator_ids: list[int],
) -> dict[str, np.ndarray]:
    model.opt.timestep = float(cfg["sim"]["dt"])
    kp_cfg = cfg["control"]["kp"]
    kd_cfg = cfg["control"]["kd"]
    torque_limit = float(cfg["control"]["torque_limit"])
    kp = np.zeros(len(joint_names_leg_major), dtype=np.float32)
    kd = np.zeros(len(joint_names_leg_major), dtype=np.float32)
    torque_limits = np.full(len(joint_names_leg_major), torque_limit, dtype=np.float32)
    armature = actuator_model_values(cfg, joint_names_leg_major, "armature", 0.0)

    for index, (joint_name, joint_id, actuator_id) in enumerate(zip(joint_names_leg_major, joint_ids, actuator_ids)):
        kind = mujoco_joint_kind(joint_name)
        kp[index] = float(kp_cfg[kind])
        kd[index] = float(kd_cfg[kind])
        dof_id = int(model.jnt_dofadr[joint_id])
        model.dof_armature[dof_id] = float(armature[index])
        model.dof_damping[dof_id] = 0.0
        model.dof_frictionloss[dof_id] = 0.0
        model.actuator_gainprm[actuator_id, :] = 0.0
        model.actuator_biasprm[actuator_id, :] = 0.0
        model.actuator_forcerange[actuator_id] = np.array([-torque_limit, torque_limit])
    return {
        "kp": kp,
        "kd": kd,
        "torque_limits": torque_limits,
        "armature": armature,
        "x1": actuator_model_values(cfg, joint_names_leg_major, "x1", 1.0e9),
        "x2": actuator_model_values(cfg, joint_names_leg_major, "x2", 1.0e9),
        "y1": actuator_model_values(cfg, joint_names_leg_major, "y1", torque_limit),
        "y2": actuator_model_values(cfg, joint_names_leg_major, "y2", torque_limit),
        "friction_static": actuator_model_values(cfg, joint_names_leg_major, "friction_static", 0.0),
        "friction_dynamic": actuator_model_values(cfg, joint_names_leg_major, "friction_dynamic", 0.0),
        "activation_velocity": actuator_model_values(cfg, joint_names_leg_major, "activation_velocity", 0.01),
    }


def clip_torque_speed(
    tau: np.ndarray,
    joint_vel: np.ndarray,
    torque_limits: np.ndarray,
    x1: np.ndarray,
    x2: np.ndarray,
    y1: np.ndarray,
    y2: np.ndarray,
) -> np.ndarray:
    same_direction = (joint_vel * tau) > 0.0
    max_effort = np.where(same_direction, y1, y2)
    speed_abs = np.abs(joint_vel)
    denom = np.maximum(x2 - x1, 1.0e-6)
    tn_limit = np.maximum((-max_effort / denom) * (speed_abs - x1) + max_effort, 0.0)
    max_effort = np.where(same_direction & (speed_abs >= x1), tn_limit, max_effort)
    max_effort = np.minimum(max_effort, torque_limits)
    return np.clip(tau, -max_effort, max_effort)


def apply_torque_pd(
    data: Any,
    qpos_addrs_leg_major: list[int],
    qvel_addrs_leg_major: list[int],
    target_joint_pos_leg_major: np.ndarray,
    actuator_params: dict[str, np.ndarray],
) -> np.ndarray:
    joint_pos = np.asarray([data.qpos[addr] for addr in qpos_addrs_leg_major], dtype=np.float32)
    joint_vel = np.asarray([data.qvel[addr] for addr in qvel_addrs_leg_major], dtype=np.float32)
    tau = actuator_params["kp"] * (target_joint_pos_leg_major - joint_pos) - actuator_params["kd"] * joint_vel
    friction = actuator_params["friction_static"] * np.tanh(
        joint_vel / actuator_params["activation_velocity"]
    ) + actuator_params["friction_dynamic"] * joint_vel
    tau = clip_torque_speed(
        tau - friction,
        joint_vel,
        actuator_params["torque_limits"],
        actuator_params["x1"],
        actuator_params["x2"],
        actuator_params["y1"],
        actuator_params["y2"],
    )
    for dof_addr, value in zip(qvel_addrs_leg_major, tau):
        data.qfrc_applied[dof_addr] = float(value)
    return tau


def run_simulation(cfg: dict[str, Any], config_path: Path, args: argparse.Namespace) -> None:
    import mujoco

    xml_path = resolve_path(cfg["robot"]["xml_path"], config_path)
    checkpoint_path = resolve_path(cfg["policy"]["checkpoint"], config_path)
    policy = load_policy(checkpoint_path, cfg["policy"], args.device)

    model = mujoco.MjModel.from_xml_path(str(xml_path))
    data = mujoco.MjData(model)

    joint_names = mujoco_joint_names_from_cfg(cfg)
    policy_joint_names = cfg["joint_mapping"]["policy_joint_names"]
    joint_ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name) for name in joint_names]
    if any(joint_id < 0 for joint_id in joint_ids):
        missing = [name for name, joint_id in zip(joint_names, joint_ids) if joint_id < 0]
        raise RuntimeError(f"Missing MuJoCo joints: {missing}")
    qpos_addrs_leg_major = [int(model.jnt_qposadr[joint_id]) for joint_id in joint_ids]
    qvel_addrs_leg_major = [int(model.jnt_dofadr[joint_id]) for joint_id in joint_ids]
    actuator_ids = resolve_actuator_ids(model, mujoco, joint_ids)
    sensor_slices = {
        "gyro": resolve_sensor_slice(model, mujoco, "gyro", 3),
        "orientation": resolve_sensor_slice(model, mujoco, "orientation", 4),
    }

    base_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, cfg["robot"]["base_body"])
    if base_body_id < 0:
        raise RuntimeError(f"Missing base body: {cfg['robot']['base_body']}")

    actuator_params = configure_model(model, cfg, joint_names, joint_ids, actuator_ids)

    default_by_kind = cfg["control"]["default_joint_pos"]
    default_joint_pos_model = np.array([default_by_kind[joint_kind(name)] for name in policy_joint_names], dtype=np.float32)
    default_joint_pos_leg_major = default_joint_pos_model[PER_JOINT_TO_LEG_MAJOR]
    set_initial_state(data, qpos_addrs_leg_major, qvel_addrs_leg_major, default_joint_pos_leg_major, cfg)
    data.ctrl[actuator_ids] = 0.0
    mujoco.mj_forward(model, data)

    command = command_from_config(cfg, args)
    action_scale = float(cfg["control"]["action_scale"])
    clip_actions = float(cfg["policy"]["clip_actions"])
    clip_obs = float(cfg["policy"]["clip_observations"])
    decimation = int(cfg["sim"]["decimation"])
    duration = float(cfg["sim"]["duration"] if args.duration is None else args.duration)
    policy_dt = float(cfg["sim"]["dt"]) * decimation
    last_action_model = np.zeros(len(joint_names), dtype=np.float32)
    target_joint_pos_leg_major = default_joint_pos_leg_major.copy()

    def policy_step() -> None:
        nonlocal last_action_model, target_joint_pos_leg_major
        obs = make_observation(
            data,
            sensor_slices,
            qpos_addrs_leg_major,
            qvel_addrs_leg_major,
            default_joint_pos_model,
            command,
            last_action_model,
            clip_obs,
        )
        obs_tensor = torch.from_numpy(obs).unsqueeze(0).to(args.device)
        with torch.inference_mode():
            action = policy.act_inference(obs_tensor).squeeze(0).cpu().numpy()
        last_action_model = np.clip(action, -clip_actions, clip_actions).astype(np.float32)
        target_joint_pos_model = default_joint_pos_model + last_action_model * action_scale
        target_joint_pos_leg_major = target_joint_pos_model[PER_JOINT_TO_LEG_MAJOR]

    total_steps = int(math.ceil(duration / policy_dt))
    delay_steps = max(0, int(cfg["control"].get("delay_steps", 0)))
    delayed_targets = [default_joint_pos_leg_major.copy() for _ in range(delay_steps)]
    next_print = 0.0
    start_wall_time = time.time()

    def run_step(step_id: int) -> None:
        nonlocal next_print
        step_start = time.time()
        policy_step()
        if delay_steps > 0:
            delayed_targets.append(target_joint_pos_leg_major.copy())
            applied_target_joint_pos_leg_major = delayed_targets.pop(0)
        else:
            applied_target_joint_pos_leg_major = target_joint_pos_leg_major
        for _ in range(decimation):
            apply_torque_pd(
                data,
                qpos_addrs_leg_major,
                qvel_addrs_leg_major,
                applied_target_joint_pos_leg_major,
                actuator_params,
            )
            mujoco.mj_step(model, data)
        sim_time = (step_id + 1) * policy_dt
        if args.print_rate > 0 and sim_time >= next_print:
            base_pos = np.array(data.xpos[base_body_id])
            print(
                f"t={sim_time:6.2f}s "
                f"cmd=({command[0]:+.2f},{command[1]:+.2f},{command[2]:+.2f}) "
                f"base_pos=({base_pos[0]:+.3f},{base_pos[1]:+.3f},{base_pos[2]:.3f})"
            )
            next_print += args.print_rate
        if args.real_time:
            sleep_time = policy_dt - (time.time() - step_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

    if args.headless:
        for step in range(total_steps):
            run_step(step)
    else:
        import mujoco.viewer

        with mujoco.viewer.launch_passive(model, data) as viewer:
            for step in range(total_steps):
                if not viewer.is_running():
                    break
                args.real_time = True
                run_step(step)
                viewer.sync()

    elapsed = time.time() - start_wall_time
    print(f"Finished {total_steps} policy steps in {elapsed:.2f}s wall time.")


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    validate_config(cfg, args.config)
    if args.dry_run:
        command = command_from_config(cfg, args)
        print(f"Config OK: {args.config}")
        print(f"Scene XML: {cfg['robot']['xml_path']}")
        print(f"Checkpoint: {cfg['policy'].get('checkpoint') or '<not set>'}")
        print(f"Command: vx={command[0]:.3f}, vy={command[1]:.3f}, yaw={command[2]:.3f}")
        return
    if not cfg["policy"].get("checkpoint"):
        raise ValueError("policy.checkpoint is empty. Set it in the YAML config before running sim2sim.")
    run_simulation(cfg, args.config, args)


if __name__ == "__main__":
    main()
