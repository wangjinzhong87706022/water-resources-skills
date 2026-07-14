"""Cross-platform path resolver for water-resources skills.

Priority:
  1. WATER_RESOURCES_ROOT env var (deployment contract)        ← 主路径
  2. WATER_RESOURCES_LIB / _SHARED explicit overrides          ← 特殊布局
  3. Candidate-root fallback (dev convenience)                 ← 兜底

The LLM runtime snippet (see SKILL.md "标准导入片段") uses path #1
directly; this module adds #2/#3 for offline scripts and robustness.
"""
import os
from pathlib import Path

_LIB_MARKER = "db.py"
_SHARED_MARKER = "db_connection.md"

# 兜底候选根（仅当环境变量未设时遍历，dev/未配置环境的便利）
_KNOWN_ROOTS = (
    "/mnt/skills",
    "/opt/git/water-resources-skills/skills",
    str(Path.home() / ".hermes" / "skills" / "water-resources"),
)


def _root() -> Path | None:
    r = os.environ.get("WATER_RESOURCES_ROOT")
    if r and Path(r).is_dir():
        return Path(r)
    for c in _KNOWN_ROOTS:                       # fallback
        if (Path(c) / "lib" / _LIB_MARKER).exists():
            return Path(c)
    return None


def locate_lib() -> Path:
    # 覆盖优先
    ovr = os.environ.get("WATER_RESOURCES_LIB")
    if ovr and (Path(ovr) / _LIB_MARKER).exists():
        return Path(ovr)
    r = _root()
    if r and (r / "lib" / _LIB_MARKER).exists():
        return r / "lib"
    raise RuntimeError(
        "water-resources lib/ not found. Set WATER_RESOURCES_ROOT "
        "(or WATER_RESOURCES_LIB) in the deployment environment."
    )


def locate_shared() -> Path:
    ovr = os.environ.get("WATER_RESOURCES_SHARED")
    if ovr and (Path(ovr) / _SHARED_MARKER).exists():
        return Path(ovr)
    r = _root()
    if r and (r / "shared" / _SHARED_MARKER).exists():
        return r / "shared"
    raise RuntimeError("water-resources shared/ not found.")
