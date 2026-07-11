# SPDX-License-Identifier: Apache-2.0
"""Uniubi robot asset configurations."""

from __future__ import annotations

import os

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg
from isaaclab.utils import configclass

from uniubi_rl_lab.assets.robots.uniubi_actuators import UniubiActuatorCfg_Cyvet

@configclass
class UniubiUsdFileCfg(sim_utils.UsdFileCfg):
    """USD spawn configuration for Uniubi robots."""

    activate_contact_sensors: bool = True
    rigid_props = sim_utils.RigidBodyPropertiesCfg(
        disable_gravity=False,
        retain_accelerations=False,
        linear_damping=0.0,
        angular_damping=0.0,
        max_linear_velocity=1000.0,
        max_angular_velocity=1000.0,
        max_depenetration_velocity=1.0,
    )
    articulation_props = sim_utils.ArticulationRootPropertiesCfg(
        enabled_self_collisions=False,
        solver_position_iteration_count=4,
        solver_velocity_iteration_count=1,
    )


CYVET_USD_PATH = os.path.join(os.path.dirname(__file__), "cyvet", "cyvet.usd")
UNIUBI_CYVET_CFG = ArticulationCfg(
    spawn=UniubiUsdFileCfg(usd_path=CYVET_USD_PATH),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.42),
        joint_pos={
            ".*_ABAD_JOINT": 0.0,
            ".*_HIP_JOINT": 0.8,
            ".*_KNEE_JOINT": -1.58,
        },
        joint_vel={".*": 0.0},
    ),
    soft_joint_pos_limit_factor=0.9,
    actuators={
        "legs": UniubiActuatorCfg_Cyvet(
            joint_names_expr=[
                ".*_ABAD_JOINT",
                ".*_HIP_JOINT",
                ".*_KNEE_JOINT",
            ],
            stiffness=35.0,
            damping=1.0,
            effort_limit=48.0,
            velocity_limit=22.0,
            velocity_limit_sim=22.0,
            min_delay=0,
            max_delay=2,
        ),
    },
)
