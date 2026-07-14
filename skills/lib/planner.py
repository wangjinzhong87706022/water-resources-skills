"""Execution strategy planner for multi-Skill queries.

Builds a dependency graph from predefined rules, performs topological sort,
and groups skills into parallel execution batches.

Usage:
    from planner import plan_execution
    from db import query  # lib/ 同目录，无需 sys.path 操作

    plan = plan_execution(["rainfall", "water-situation", "water-warning"])
    # {"steps": [["rainfall", "water-situation"], ["water-warning"]]}
"""

from collections import defaultdict, deque

# Business dependency rules: skill -> list of skills it depends on
BUSINESS_DEPENDENCIES = {
    "rainfall":            [],                          # 降雨无前置依赖
    "water-situation":     [],                          # 水位无前置依赖
    "water-quality":       [],                          # 水质无前置依赖
    "water-forecast":      [],                          # 预测无前置依赖
    "gate-pump-operation": [],                          # 闸泵无前置依赖
    "water-warning":       ["water-situation"],         # 预警依赖水位数据
}

# Causal rules: skill_A output is useful for skill_B input
CAUSAL_RULES = {
    ("rainfall", "water-situation"):     1.0,   # 降雨→水位
    ("water-situation", "water-warning"): 1.0,  # 水位→预警
    ("water-quality", "water-warning"):  1.0,   # 水质→水质预警
    ("water-situation", "water-quality"): 0.7,  # 水位→水质（弱）
    ("gate-pump-operation", "water-situation"): 0.9,  # 闸泵→水位
    ("water-forecast", "water-situation"): 0.9,  # 预测→实际水位对比
}

# Skill -> database tables mapping
SKILL_TABLES = {
    "water-situation":     ["st_river_r", "st_stbprp_b", "st_rvfcch_b"],
    "rainfall":            ["st_pptn_r", "st_stbprp_b"],
    "water-quality":       ["wq_pcp_d", "wq_wqsinf_b", "st_stbprp_b"],
    "water-forecast":      ["st_mx_preset_cal_r", "st_mx_taskid_r", "st_stbprp_b"],
    "gate-pump-operation": ["st_gate_r", "st_was_r", "st_pump_r", "st_pump_pa", "st_stbprp_b"],
    "water-warning":       ["st_river_r", "st_rvfcch_b", "st_stbprp_b", "wq_pcp_d"],
}

# Known skills
ALL_SKILLS = list(BUSINESS_DEPENDENCIES.keys())


def plan_execution(skills):
    """Plan execution order for a list of skills.

    Args:
        skills: List of skill names involved in the query.

    Returns:
        Dict with:
          - "strategy": "single" | "parallel" | "serial" | "hybrid"
          - "steps": List of groups. Each group is a list of skill names
            that can execute in parallel. Groups execute sequentially.
    """
    skills = [s for s in skills if s in ALL_SKILLS]
    if not skills:
        return {"strategy": "single", "steps": []}
    if len(skills) == 1:
        return {"strategy": "single", "steps": [skills]}

    # Build dependency graph (only among requested skills)
    # BUSINESS_DEPENDENCIES defines execution order (skill needs other's output)
    # CAUSAL_RULES define data relationships (used in fusion, NOT execution)
    deps = {s: set() for s in skills}
    for s in skills:
        for dep in BUSINESS_DEPENDENCIES.get(s, []):
            if dep in skills:
                deps[s].add(dep)

    # Topological sort with Kahn's algorithm
    in_degree = {s: len(deps[s]) for s in skills}
    queue = deque(s for s in skills if in_degree[s] == 0)
    ordered = []

    while queue:
        # All skills in queue have zero in-degree -> can run in parallel
        batch = sorted(queue)  # sorted for determinism
        ordered.append(batch)
        next_queue = deque()
        for s in batch:
            for t in skills:
                if s in deps[t]:
                    in_degree[t] -= 1
                    if in_degree[t] == 0:
                        next_queue.append(t)
        queue = next_queue

    # Detect cycle: if not all skills processed
    processed = sum(len(b) for b in ordered)
    if processed < len(skills):
        # Fallback: treat remaining as parallel
        remaining = [s for s in skills if s not in [x for b in ordered for x in b]]
        if remaining:
            ordered.append(remaining)

    strategy = "hybrid"
    if len(ordered) == 1:
        strategy = "parallel"
    elif all(len(b) == 1 for b in ordered):
        strategy = "serial"

    return {"strategy": strategy, "steps": ordered}


def get_shared_tables(skills):
    """Return tables shared by multiple skills in the list."""
    table_skills = defaultdict(list)
    for s in skills:
        for t in SKILL_TABLES.get(s, []):
            table_skills[t].append(s)
    return {t: ss for t, ss in table_skills.items() if len(ss) > 1}


def get_skill_dependencies(skill):
    """Return direct dependencies and dependents for a skill."""
    deps = BUSINESS_DEPENDENCIES.get(skill, [])
    dependents = [s for s, d in BUSINESS_DEPENDENCIES.items() if skill in d]
    causal_deps = [dst for (src, dst), st in CAUSAL_RULES.items() if src == skill and st >= 0.9]
    causal_srcs = [src for (src, dst), st in CAUSAL_RULES.items() if dst == skill and st >= 0.9]
    return {
        "depends_on": list(set(deps + causal_srcs)),
        "depended_by": list(set(dependents + causal_deps)),
    }
