# Third-Party Notices

This repository contains original Uniubi code and a small set of files derived from
or adapted from third-party projects. Files with their own SPDX license identifier,
copyright header, or license notice remain under those terms.

## Isaac Lab Derived Files

The following files retain Isaac Lab BSD-3-Clause notices:

- `.vscode/tools/setup_vscode.py`
- `pyproject.toml`
- `scripts/list_envs.py`
- `scripts/random_agent.py`
- `scripts/zero_agent.py`
- `scripts/rsl_rl/cli_args.py`
- `scripts/rsl_rl/play.py`
- `scripts/rsl_rl/train.py`
- `source/uniubi_rl_lab/setup.py`
- `source/uniubi_rl_lab/uniubi_rl_lab/__init__.py`
- `source/uniubi_rl_lab/uniubi_rl_lab/ui_extension_example.py`
- `source/uniubi_rl_lab/uniubi_rl_lab/tasks/__init__.py`
- `source/uniubi_rl_lab/uniubi_rl_lab/tasks/locomotion/agents/__init__.py`
- `source/uniubi_rl_lab/uniubi_rl_lab/tasks/locomotion/agents/rsl_rl_ppo_cfg.py`
- `source/uniubi_rl_lab/uniubi_rl_lab/tasks/locomotion/robots/cyvet/__init__.py`

Copyright:

```text
As stated in each file header, copyright belongs to the Isaac Lab Project Developers.
```

License:

```text
BSD 3-Clause License

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## External Dependencies

This repository depends on external projects such as Isaac Sim, Isaac Lab, RSL-RL,
PyTorch, MuJoCo, and their dependencies. They are not vendored here and remain
under their own license terms.

## Assets, Data, And Weights

Robot model assets included in this repository are provided for simulation and
training workflows. Datasets, trained weights, generated artifacts, and any
third-party assets must keep their own license notices when distributed.
