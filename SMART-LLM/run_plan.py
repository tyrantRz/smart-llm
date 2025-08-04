#!/usr/bin/env python3
"""
执行 SMART-LLM 生成的 code_plan.py
用法:  python run_plan.py path/to/code_plan.py <floor_id>
"""

import sys, types, pathlib
from ai2thor.controller import Controller   
from importlib.machinery import SourceFileLoader   


# ------------------------------------------------------------
# 找到项目根目录并加入 sys.path，确保能 import resources.*
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# 显式加载 aithor_connect/aithor_connect.py → 模块对象 ac_mod
ac_file = ROOT / "data" / "aithor_connect" / "aithor_connect.py"

if not ac_file.exists():
    sys.exit(f"[ERR] 找不到 {ac_file}")

loader = SourceFileLoader("aithor_connect", ac_file.as_posix())
ac_mod = types.ModuleType(loader.name)
loader.exec_module(ac_mod)            # ac_mod 里就含有 GoToObject 等真正实现
# ------------------------------------------------------------
        
# ---------- 参数 ----------
if len(sys.argv) != 3:
    sys.exit("Usage: python run_plan.py <code_plan.py> <floor_id>")
plan_path = pathlib.Path(sys.argv[1]).resolve()
floor_id  = int(sys.argv[2])

# ---------- 启动 AI2-THOR ----------
controller = ai2thor.controller.Controller(
    scene=f"FloorPlan{floor_id}",
    agentMode="default",
    visibilityDistance=1.5,
    gridSize=0.25,
    width=300, height=300
)

# ---------- objects & robots ----------
objects = [
    {"name": o["objectType"], "mass": o["mass"]}
    for o in controller.last_event.metadata["objects"]
]

import resources.robots as robots_mod
robots = robots_mod.robots

# ---------- 引入真正的动作实现 ----------
# actions 实际在 aithor_connect/aithor_connect.py
ac_mod = importlib.import_module("aithor_connect.aithor_connect")
# 让里面用到的全局 controller 指向当前实例
ac_mod.controller = controller

# ---------- 构造 skills 伪模块 ----------
skills_mod            = types.ModuleType("skills")
exported_callables    = {
    name: obj for name, obj in ac_mod.__dict__.items()
    if callable(obj) and not name.startswith("_")
}
skills_mod.__dict__.update(exported_callables)
sys.modules["skills"] = skills_mod            # 供 code_plan.py 导入

# ---------- 执行 code_plan ----------
exec_globals = {
    "robots":     robots,
    "objects":    objects,
    "controller": controller,
}
exec_globals.update(exported_callables)       

print(f"=== Exec {plan_path.name} on FloorPlan{floor_id} ===")
exec(plan_path.read_text("utf8"), exec_globals)
print("=== Done ===")
