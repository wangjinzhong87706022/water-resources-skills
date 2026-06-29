#!/usr/bin/env python3
"""Harness Adapter — 编程式执行单个 test case,拿 trajectory + tool_stats。

修复 evaluate_skills.py 的两个问题:
1. 旧 run_hermes_oneshot 用 `hermes -z` subprocess,拿不到 messages/tool_calls/trajectory。
2. hermes -z 的 oneshot 路径丢弃 -s skill(main.py:11979 不传 args.skills),
   旧评测根本没加载 skill。

本模块改用编程式 API(借鉴 batch_runner._process_single_prompt),通过
build_preloaded_skills_prompt 把 skill 注入 ephemeral_system_prompt(修 #2),
并直接拿 result["messages"] → trajectory + tool_stats(修 #1)。

依赖:能 import hermes(仓库根运行 / pip install -e .)。顶部不 import hermes,
只在 run_case 内 lazy import —— 这样 evaluate_skills.py 顶部 import 本模块时,
即使 hermes 未装也不会崩(--engine subprocess 仍可用)。
"""

import os
import time
from typing import Any, Optional


def _final_text_from_messages(messages: list) -> str:
    """从 OpenAI messages 提取最后一条 assistant 回答的纯文本。
    content 可能是 str 或 list of blocks({"type":"text","text":...})。"""
    for msg in reversed(messages or []):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    t = block.get("text") or block.get("content") or ""
                    if t:
                        parts.append(str(t))
                elif isinstance(block, str):
                    parts.append(block)
            joined = "\n".join(parts).strip()
            if joined:
                return joined
    return ""


def run_case(
    case,
    *,
    model: str,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_iterations: int = 12,
    enabled_toolsets: Optional[list] = None,
) -> dict:
    """编程式执行单个 test case。

    Args:
        case: TestCase dataclass(需有 .question / .skill / .index)
        model: 模型名(必填)
        provider/base_url/api_key: 可选,覆盖 config
        max_iterations: tool-calling 迭代上限(编程式不做硬 wall-clock 超时,
            靠 max_iterations 控制时长;硬超时留待后续)
        enabled_toolsets: 可选,限制工具集;None 走 config

    Returns:
        dict: {success, final_response, actual_sql(""), trajectory, raw_messages,
               tool_stats, reasoning_stats, completed, api_calls, duration_sec, error,
               loaded_skills, missing_skills}
        actual_sql 留空,由调用方用 evaluate_skills.extract_sql_from_response 填。
    """
    # lazy import(hermes 未装时报错而非整个脚本崩)
    from run_agent import AIAgent
    from agent.skill_commands import build_preloaded_skills_prompt
    from batch_runner import _extract_tool_stats, _extract_reasoning_stats

    task_id = f"eval_{getattr(case, 'skill', 'unknown')}_{getattr(case, 'index', 0)}"

    # ---- 修 bug #2:注入 skill 到 ephemeral_system_prompt ----
    ephemeral_system_prompt = None
    loaded_skills: list = []
    missing_skills: list = []
    skill_id = getattr(case, "skill", None)
    if skill_id:
        try:
            prompt_text, loaded_names, missing = build_preloaded_skills_prompt(
                [skill_id], task_id=task_id
            )
            loaded_skills = loaded_names or []
            missing_skills = missing or []
            if loaded_skills and not missing_skills:
                ephemeral_system_prompt = prompt_text
        except Exception as e:
            missing_skills = [f"{skill_id} (load error: {e})"]

    start = time.time()

    # YOLO env(同 run_hermes_oneshot:跳过审批弹窗)
    old_env = dict(os.environ)
    os.environ["HERMES_YOLO_MODE"] = "1"
    os.environ["HERMES_ACCEPT_HOOKS"] = "1"

    try:
        agent = AIAgent(
            base_url=base_url,
            api_key=api_key,
            model=model,
            provider=provider,
            max_iterations=max_iterations,
            enabled_toolsets=enabled_toolsets,
            save_trajectories=False,  # 自己落盘
            ephemeral_system_prompt=ephemeral_system_prompt,
            skip_context_files=True,  # 不污染轨迹(SOUL.md/AGENTS.md)
            skip_memory=True,         # eval 不用持久记忆
            quiet_mode=True,
        )
        result = agent.run_conversation(case.question, task_id=task_id)

        messages = result.get("messages", [])
        completed = result.get("completed", False)
        trajectory = agent._convert_to_trajectory_format(
            messages, case.question, completed
        )
        tool_stats = _extract_tool_stats(messages)
        reasoning_stats = _extract_reasoning_stats(messages)
        final_response = _final_text_from_messages(messages)

        return {
            "success": True,
            "final_response": final_response,
            "actual_sql": "",
            "trajectory": trajectory,
            "raw_messages": messages,
            "tool_stats": tool_stats,
            "reasoning_stats": reasoning_stats,
            "completed": completed,
            "api_calls": result.get("api_calls", 0),
            "duration_sec": round(time.time() - start, 2),
            "error": "",
            "loaded_skills": loaded_skills,
            "missing_skills": missing_skills,
        }
    except Exception as e:
        return {
            "success": False,
            "final_response": f"[ERROR]: {e}",
            "actual_sql": "",
            "trajectory": [],
            "raw_messages": [],
            "tool_stats": {},
            "reasoning_stats": {},
            "completed": False,
            "api_calls": 0,
            "duration_sec": round(time.time() - start, 2),
            "error": f"{e}",
            "loaded_skills": loaded_skills,
            "missing_skills": missing_skills,
        }
    finally:
        os.environ.clear()
        os.environ.update(old_env)
