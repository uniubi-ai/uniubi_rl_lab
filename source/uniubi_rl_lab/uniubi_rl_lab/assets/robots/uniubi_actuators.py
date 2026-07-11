# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import MISSING
from typing import TypeAlias

import torch

from isaaclab.actuators import DelayedPDActuator, DelayedPDActuatorCfg
from isaaclab.utils import configclass
from isaaclab.utils.types import ArticulationActions

JointParameter: TypeAlias = float | dict[str, float]


class UniubiActuator(DelayedPDActuator):
    """Uniubi PD actuator with torque-speed envelope and explicit friction."""

    cfg: UniubiActuatorCfg

    armature: torch.Tensor
    """The armature of the actuator joints. Shape is ``(num_envs, num_joints)``."""

    def __init__(self, cfg: UniubiActuatorCfg, *args, **kwargs):
        super().__init__(cfg, *args, **kwargs)

        self._joint_vel = torch.zeros_like(self.computed_effort)
        effort_limit_cfg = getattr(cfg, "effort_limit", None)
        self._effort_limit = self._parse_joint_parameter(
            effort_limit_cfg if effort_limit_cfg is not None else 30.0,
            30.0,
        )
        self._effort_y1 = self._parse_joint_parameter(cfg.Y1, 1e9)
        self._effort_y2 = self._parse_joint_parameter(cfg.Y2, cfg.Y1)
        self._velocity_x1 = self._parse_joint_parameter(cfg.X1, 1e9)
        self._velocity_x2 = self._parse_joint_parameter(cfg.X2, 1e9)
        self._friction_static = self._parse_joint_parameter(cfg.Fs, 0.0)
        self._friction_dynamic = self._parse_joint_parameter(cfg.Fd, 0.0)
        self._base_friction_static = self._friction_static.clone()
        self._base_friction_dynamic = self._friction_dynamic.clone()
        self._activation_vel = self._parse_joint_parameter(cfg.Va, 0.01)

    def compute(
        self, control_action: ArticulationActions, joint_pos: torch.Tensor, joint_vel: torch.Tensor
    ) -> ArticulationActions:
        self._compute_nominal_effort(control_action, joint_pos, joint_vel)
        self.applied_effort = self._clip_effort(self.applied_effort)

        control_action.joint_positions = None
        control_action.joint_velocities = None
        control_action.joint_efforts = self.applied_effort
        return control_action

    def _compute_nominal_effort(
        self, control_action: ArticulationActions, joint_pos: torch.Tensor, joint_vel: torch.Tensor
    ) -> torch.Tensor | None:
        self._joint_vel[:] = joint_vel

        control_action.joint_positions = self.positions_delay_buffer.compute(control_action.joint_positions)
        control_action.joint_velocities = self.velocities_delay_buffer.compute(control_action.joint_velocities)
        control_action.joint_efforts = self.efforts_delay_buffer.compute(control_action.joint_efforts)

        control_action = super(DelayedPDActuator, self).compute(control_action, joint_pos, joint_vel)

        self.applied_effort -= (
            self._friction_static * torch.tanh(joint_vel / self._activation_vel) + self._friction_dynamic * joint_vel
        )
        return None

    def _clip_effort(self, effort: torch.Tensor) -> torch.Tensor:
        same_direction = (self._joint_vel * effort) > 0
        max_effort = torch.where(same_direction, self._effort_y1, self._effort_y2)
        motoring_over_x1 = same_direction & (self._joint_vel.abs() >= self._velocity_x1)
        max_effort = torch.where(motoring_over_x1, self._compute_effort_limit(max_effort), max_effort)
        max_effort = torch.minimum(max_effort, self._effort_limit)
        return torch.clip(effort, -max_effort, max_effort)

    def _compute_effort_limit(self, max_effort: torch.Tensor) -> torch.Tensor:
        k = -max_effort / (self._velocity_x2 - self._velocity_x1)
        limit = k * (self._joint_vel.abs() - self._velocity_x1) + max_effort
        return limit.clip(min=0.0)

    def set_tn_curve(
        self,
        env_ids: torch.Tensor | list[int] | tuple[int, ...] | None = None,
        x1: torch.Tensor | float | None = None,
        x2: torch.Tensor | float | None = None,
        y1: torch.Tensor | float | None = None,
        y2: torch.Tensor | float | None = None,
    ) -> None:
        target_env_ids = self._resolve_env_ids(env_ids)
        self._assign_curve_parameter(self._velocity_x1, target_env_ids, x1)
        self._assign_curve_parameter(self._velocity_x2, target_env_ids, x2)
        self._assign_curve_parameter(self._effort_y1, target_env_ids, y1)
        self._assign_curve_parameter(self._effort_y2, target_env_ids, y2)

    def set_friction_params(
        self,
        env_ids: torch.Tensor | list[int] | tuple[int, ...] | None = None,
        fs: torch.Tensor | float | None = None,
        fd: torch.Tensor | float | None = None,
    ) -> None:
        target_env_ids = self._resolve_env_ids(env_ids)
        self._assign_curve_parameter(self._friction_static, target_env_ids, fs)
        self._assign_curve_parameter(self._friction_dynamic, target_env_ids, fd)

    def _resolve_env_ids(self, env_ids: torch.Tensor | list[int] | tuple[int, ...] | None) -> torch.Tensor | slice:
        if env_ids is None:
            return slice(None)
        env_ids_tensor = torch.as_tensor(env_ids, device=self.computed_effort.device, dtype=torch.long)
        if env_ids_tensor.numel() == 0:
            return env_ids_tensor
        return env_ids_tensor

    def _assign_curve_parameter(
        self,
        parameter: torch.Tensor,
        env_ids: torch.Tensor | slice,
        value: torch.Tensor | float | None,
    ) -> None:
        if value is None:
            return
        if isinstance(env_ids, torch.Tensor) and env_ids.numel() == 0:
            return
        target = parameter if isinstance(env_ids, slice) else parameter[env_ids]
        value_tensor = torch.as_tensor(value, device=parameter.device, dtype=parameter.dtype)
        expanded_value = self._expand_curve_value(value_tensor, target)
        if isinstance(env_ids, slice):
            parameter[:] = expanded_value
        else:
            parameter[env_ids] = expanded_value

    @staticmethod
    def _expand_curve_value(value: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if value.ndim == 0:
            return torch.full_like(target, float(value.item()))
        if value.shape == target.shape:
            return value
        if value.ndim == 1:
            if value.shape[0] == target.shape[0]:
                return value.unsqueeze(-1).expand_as(target)
            if value.shape[0] == target.shape[1]:
                return value.unsqueeze(0).expand_as(target)
        if value.ndim == 2 and value.shape[0] == target.shape[0] and value.shape[1] == 1:
            return value.expand_as(target)
        raise ValueError(f"Cannot broadcast actuator parameter with shape {tuple(value.shape)} to {tuple(target.shape)}")


@configclass
class UniubiActuatorCfg(DelayedPDActuatorCfg):
    """Configuration for Uniubi actuators."""

    class_type: type = UniubiActuator

    armature: JointParameter = 0.0
    """Reflected armature for the actuator joints."""

    X1: JointParameter = 1e9
    """Maximum speed at full torque (rad/s)."""

    X2: JointParameter = 1e9
    """No-load speed (rad/s)."""

    Y1: JointParameter = MISSING
    """Peak torque in the same direction as velocity (N*m)."""

    Y2: JointParameter | None = None
    """Peak torque in the opposite direction of velocity (N*m)."""

    Fs: JointParameter = 0.0
    """Static friction coefficient."""

    Fd: JointParameter = 0.0
    """Dynamic friction coefficient."""

    Va: JointParameter = 0.01
    """Velocity at which the friction is fully activated."""


@configclass
class UniubiActuatorCfg_Cyvet(UniubiActuatorCfg):
    """Cyvet actuator parameters."""

    X1 = 15.0
    X2 = 21.0
    Y1 = 48.0
    Y2 = 48.0
    Va = 0.01
    armature = {
        ".*_ABAD_JOINT": 0.0174989,
        ".*_HIP_JOINT": 0.0158000,
        ".*_KNEE_JOINT": 0.0173718,
    }
    Fs = {
        ".*_ABAD_JOINT": 0.2292320,
        ".*_HIP_JOINT": 0.2127050,
        ".*_KNEE_JOINT": 0.2729870,
    }
    Fd = {
        ".*_ABAD_JOINT": 0.0233946,
        ".*_HIP_JOINT": 0.0038715,
        ".*_KNEE_JOINT": 0.0136532,
    }
