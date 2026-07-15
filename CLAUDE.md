# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A collection of **water-resources (水利) domain skills** — Markdown instruction packages that teach an LLM how to query Yangzhou (扬州) water-conservancy data. **Skills are not runnable programs**; they are `SKILL.md` + `references/` knowledge consumed at runtime by two external systems:

- **Path A — `dataagent`:** a Java web app (port 8080) that turns natural-language questions → SQL → executes against MySQL.
- **Path B — `hermes-agent`:** a CLI/API that activates skills via slash commands (`/water-situation …`) and generates SQL from the loaded skill context.

The Python under `skills/lib/` and `skills/scripts/` is the supporting code: a shared DB helper, the multi-skill orchestration engine (the patent's core), and an evaluation/test harness.

## Environment setup

- **Python dep:** `pip install pymysql` (the only runtime dependency; read-only MySQL access).
- **DB credentials:** copy `.env.example` → `.env` and fill `SL323_DB_PASSWORD`. `.env` is gitignored — never commit it. `skills/lib/db.py` and all scripts read these via `os.environ`.
- **DB host:** MySQL `192.168.100.103:3306`, **read-only** (root), UTC+8. Four databases: `sl323` (core: level/rainfall/gates/stations/flood), `sl325` (water quality), `slztk` (forecast models), `powerelf_data` (Powerelf platform, referenced but out of scope).
- **Coverage:** `sl323` is **Yangzhou-only** (station admin codes start with `3210`). Say so upfront for out-of-area queries instead of searching repeatedly.

## Common commands

```bash
# Run a single skill question manually via hermes (non-interactive)
hermes -z -s water-situation "古运河有哪些水位测站"
hermes -z -s water-situation,water-visualization "古运河最近30天水位趋势图"   # data + viz combined

# Evaluate skills against the 98 test cases (run from skills/ dir)
python3 scripts/evaluate_skills.py                       # full run
python3 scripts/evaluate_skills.py --skill water-situation --level L1 --range 1-10
python3 scripts/evaluate_skills.py --dry-run             # parse only, no execution
python3 scripts/evaluate_skills.py --validate-sql        # check expected SQL runs
python3 scripts/evaluate_skills.py --output reports/eval_run   # custom report dir

# Selection/regression gate: backup skill files → run candidate → diff vs baseline → restore
python3 scripts/run_gate.py

# Ablation experiments (long, 2-3h) → regenerates patent doc tables
nohup bash scripts/ablation-autopilot.sh > /tmp/ablation-run.log 2>&1 &
tail -f /tmp/ablation-run.log
```

There is no build step, lint, or test runner — "tests" = the eval harness above. Reports are written to `skills/reports/` (e.g. `l1_eval/`, `l3_eval/`, `gate/`, `ablation/`, `autoresearch/`).

## Configuration（DeerFlow 运行时）

- **env 来源**：DeerFlow 以 `make dev` 启动（非 systemd），backend 进程 cwd=backend，通过 `app_config.py` 的 `load_dotenv()` 读 `deer-flow/backend/.env`。`/etc/default/deerflow-env` 不被任何 service 引用，是死文件。
- **`WATER_RESOURCES_ROOT`**（写在 `deer-flow/backend/.env`）必须指向含 `lib/` 的真实目录：`/opt/git/water-resources-skills/skills`。LLM 运行时代码用 `sys.path.insert(0, $WATER_RESOURCES_ROOT/lib)`；sandbox 的 `execute_command` 是 host bash，宿主机绝对路径透传、不走 `/mnt/skills` 路径翻译与逃逸检查。**不要用 `/mnt/skills`** —— 那是遗留 symlink → `deer-flow/skills`，其下无 `lib/`。
- **db.py 超时**：`query()` 的超时经 `_connect(read_timeout=timeout)` 实现（连接级）。`pymysql` 的 `cursor.execute()` **不接受** `timeout=` 参数，切勿加回。
- **db.py 密码回退（sandbox env 清洗，重要）**：DeerFlow sandbox 子进程的环境经 `env_policy.build_sandbox_env()` 清洗，凡匹配 `*PASSWORD*/*KEY*/*SECRET*/*TOKEN*/*PASSWD*/*CREDENTIAL*/*DSN*` 的变量一律剥离（issue #3861，防止 skill 脚本窃取平台密钥）。故 `SL323_DB_PASSWORD` 在 sandbox 里**不可见**，db.py 不能只靠 `os.environ`。db.py 已加文件回退：环境变量为空时从仓库根 `.env`（gitignored，相对 `__file__` 定位）读。**密码在 sandbox 里的权威来源是 `water-resources-skills/.env`，不是 `deer-flow/backend/.env`**（后者虽由 `load_dotenv()` 载入 backend 进程，但传给 sandbox 前已被清洗）。db.py 在 backend 目录之外，由 `execute_command` 每次 spawn 的新 python 重新 import，改完下次查询即生效，无需重启。
- **生效方式**：改 `backend/.env` 会触发 uvicorn `--reload`（`--reload-include='.env'`）自动重载；`db.py` 在 backend 目录之外，由 `execute_command` 每次 spawn 的新 python 重新 import，改完下次查询即生效，无需手动重启。
- **加载额外 skill**：DeerFlow 扫描根是 `water-resources-skills/skills/public`（config.yaml `skills.path`），用 `os.walk(followlinks=True)` 递归发现。要把 skill 加进来，拷**实目录**进 `public/`（软链接在 sandbox `read_file` 路径翻译时会因逃逸检查失败）。

## Architecture: the big picture

### Skill layer (`skills/<name>/`)

Three tiers of skills, each a self-contained `SKILL.md` + optional `references/`:

| Tier | Skills | Role |
|------|--------|------|
| **Data** (6) | `water-situation`, `rainfall`, `water-quality`, `water-forecast`, `gate-pump-operation`, `water-warning` | Each maps a business domain to a set of MySQL tables and owns its query patterns. |
| **Orchestration** | `water-fusion` | Cross-domain fusion — the patent's core. |
| **Visualization** | `water-visualization`, `build-dashboard`, `create-viz`, `data-context-extractor` | The last three are newer (untracked). |

**Canonical `SKILL.md` structure** — when editing or creating a skill, follow this layout (see `water-situation/SKILL.md` for the reference): YAML frontmatter (`name`, `description`, `version`, `metadata.hermes.tags` + `category: water-resources`) → `# Title` → `## When to Use` (scenario table) → `## Prerequisites` → `## Pitfalls` → `## References` → `## Workflow` → `## Validation Gate`. Each data skill ends with a **Validation Gate** (row-count sanity + value-range checks + confidence rating) that must pass before delivery.

### Orchestration engine (`skills/lib/`)

The patent's innovation, implemented in three modules:

- **`planner.py`** — `plan_execution(skills)` builds a dependency graph and returns parallel execution batches via topological sort (Kahn's algorithm). **Critical design: dual-graph separation** — `BUSINESS_DEPENDENCIES` (execution order, e.g. `water-warning` needs `water-situation`) is kept separate from `CAUSAL_RULES` (data relationships with strength scores, used only by fusion). Conflating them is the ablation's `no-dual-graph` failure mode.
- **`fusion.py`** — the fusion pipeline: `correlate()` → `fuse()` → `detect_conflicts()` → `resolve_conflicts()`. Correlation runs on three dimensions (**time / spatial / business**); `fuse()` auto-picks the strongest dimension and aligns by time bucket, normalized station, or business rule.
- **`db.py`** — the single shared DB helper. **All queries must go through `query()` / `query_multi()`** — never hand-write pymysql.

### Shared knowledge (`skills/shared/`)

Cross-cutting docs every skill references: `sql_safety_rules.md`, `sql_patterns.md`, `sql_quality_check.md`, `analysis_validation.md`, `db_connection.md`, plus `common_schema/` (the tables reused across many skills: `st_stbprp_b` = stations, `st_rvfcch_b` = flood indicators).

## Critical conventions & pitfalls

- **DB helper path (environment variable method):** Load it with `sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib')); from db import query`. The `WATER_RESOURCES_ROOT` environment variable (set by deployment) points to the `skills/` directory; `lib/` and `shared/` are derived from it. See `skills/docs/skill-file-reference-design.md` for the full design.
- **DB helper path (offline scripts):** `sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lib')); from bootstrap import locate_lib, locate_shared; from db import query`. The `.parent.parent` navigates from `scripts/` → `skills/` → `lib/`.
- **`query()` returns `list[dict]`, not a DataFrame.** Don't call `.iterrows()`/`.groupby()`. Convert explicitly if needed: `pd.DataFrame(query(sql))`.
- **SELECT-only:** `db.py` rejects anything but `SELECT/SHOW/DESCRIBE`. SQL must have a `WHERE` (time range or station), every `JOIN` an `ON`, and a `LIMIT` (default 1000). No cartesian products, subqueries ≤3 levels.
- **Partitioned tables** (`st_river_r`, `st_was_r`, `st_pump_r`, `st_pump_pa`) are RANGE-partitioned on `tm` — **WHERE must include a `tm` range** or the query scans all partitions and times out (30s). `st_rvfcch_b` has no index; avoid joining it repeatedly.
- **Cross-domain station IDs use different encodings** (reservoir/river/gate-pump) and can't be joined directly — `fusion.py:normalize_station()` strips suffixes for name-based matching.
- **Validate before delivery.** Every skill's Workflow ends with a Validation Gate (row-count + value-range + confidence). For fusion queries, also run the row-explosion and mean-vs-median checks in `water-fusion/SKILL.md`.
- **Newer skills (`build-dashboard`, `create-viz`, `data-context-extractor`) are currently untracked** — only a `SKILL.md` each, no `references/` yet.

## Eval harness internals (`skills/scripts/`)

The harness is the test system; understanding it matters when changing skills:

- `evaluate_skills.py` parses `skills/docs/test-cases-with-sql.md` (98 cases, L1/L2/L3), runs each via `hermes -z`, and scores on SQL-generation / SQL-similarity / execution-success / result-quality. Each case has a natural-language question + expected SQL.
- `run_gate.py` (+ `gates.py`) is the **selection/regression gate**: backs up all `SKILL.md` + `references/` + `shared/*.md`, runs the candidate patch once, diffs against an existing baseline report (no baseline re-run), and restores files on exit. Failures land in `failed_trajectories.jsonl`.
- `ablation_fusion.py` removes one innovation at a time (dual-graph, adaptive time granularity, station normalization, conflict detection, fusion itself) and feeds results back into `docs/patent-application-v2.md` via `ablation-autopilot.sh`. The patent doc encodes the system's claimed innovations — ablation measures each one's contribution.
- Scripts import each other (e.g. `run_gate` imports `gates`); run them **from the `skills/` directory** so relative imports resolve.
