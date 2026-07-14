# Water-Resources Skill 文件引用设计与改造方案（DeerFlow + Hermes Agent 双平台）

**文档版本**: 1.0
**编制日期**: 2026-07-14
**范围**: 以 `water-situation` skill 为范例，设计一套同时适用于 **DeerFlow** 与 **Hermes Agent** 的 skill 文件引用机制（SKILL.md 引用、references/lib/shared 加载、Python 导入），并给出可落地的改造步骤。
**配套文档**:
- `skills/docs/deerflow-skill-path-analysis.md`（DeerFlow 路径解析源码分析）
- Hermes Agent 源码分析（`/opt/git/hermes-agent`，本文件汇总结论）

---

## 1. Overview

### 1.1 背景

本仓库（`/opt/git/water-resources-skills`）是一组**与平台无关的水利领域 skill**，其源码（`SKILL.md` + `references/` + `lib/` + `shared/` + `scripts/`）需要被**两个独立平台**消费：

- **Path A — DeerFlow**：沙箱容器，LLM 看到虚拟路径 `/mnt/skills/...`，由 `read_file` 工具自动映射到宿主真实路径。
- **Path B — Hermes Agent**：CLI/终端工具，LLM 看到宿主真实绝对路径 `/root/.hermes/skills/...`，通过 `skill_view` 与终端工具访问。

两个平台的**路径模型完全不同**，但本仓库的 skill 必须**只写一版**，在两个平台都能正确引用 `references/`、`lib/`、`shared/`。

### 1.2 核心原则

> **Skill 规范：禁止绝对路径硬编码，必须用相对路径。** 同一套 skill 可在开发/测试/生产、DeerFlow/Hermes 环境运行，部署路径变了不需要重写 SKILL.md。

本设计的全部目标，是在**遵守相对路径规范**的前提下，让相对路径在两套截然不同的解析机制下都能被正确解析。

### 1.3 现状结论（一句话）

当前 `water-situation` 的文件引用**在三处是坏的**，根因是仓库采用「`lib/`、`shared/` 与 skill 同级」的**兄弟目录布局**，但代码/文档里写的是「`lib/` 在 skill 内部」的**嵌套假设**——这两种假设在 DeerFlow 与 Hermes 下都落不到真实文件。

---

## 2. 两平台机制对照（精简版）

> 详细源码分析见 `deerflow-skill-path-analysis.md` 与 Hermes 分析结论。

| 维度 | DeerFlow | Hermes Agent |
|------|----------|--------------|
| **Skill 根来源** | `config.yaml: skills.path`（指向本仓库 `…/skills`） | `~/.hermes/skills/`（**独立副本**，非本仓库）+ `external_dirs` |
| **本仓库是否被挂载** | ✅ 直接挂载（`path` 指向它） | ❌ 默认不挂载；需手动 sync 或配 `external_dirs` |
| **LLM 看到的路径** | 虚拟 `/mnt/skills/<name>/…` | 宿主绝对路径 `/root/.hermes/skills/water-resources/<name>/…` |
| **references/ 解析** | `read_file('/mnt/skills/<skill>/references/x.md')` 自动映射 | `skill_view(name, file_path='references/x.md')` 相对 `skill_dir`，**禁止 `..`** |
| **shared/ 跨 skill 引用** | ✅ `/mnt/skills/shared/x.md`（shared 是顶层） | ⚠️ `skill_view` 无法读（`..` 被禁）；只能靠终端 `cat` 绝对路径 |
| **lib/ 加入 sys.path** | 手动（LLM 生成代码自行 insert） | 手动（hermes **从不**自动注入） |
| **`__file__` 指向** | workspace 临时暂存脚本（**不是** skill_dir） | 终端运行时为脚本真实绝对路径；`execute_code` 为暂存脚本 |
| **模板变量** | 无 | `${HERMES_SKILL_DIR}`（加载时替换为绝对 skill_dir） |
| **DeerFlow 迁移脚本策略** | 把 `lib/`+`shared/` **物理嵌入**每个 skill（自包含） | N/A |

### 2.1 关键差异引出的两条「布局路线」

- **路线 S（Sibling，兄弟目录）**：`lib/`、`shared/`、`scripts/` 与各 skill 目录同级。**Hermes 原生布局**，本仓库当前即此布局。优点：共享资源单份、无漂移；缺点：跨 skill 引用在两个平台的解析都受限制。
- **路线 E（Embedded，自包含）**：每个 skill 内嵌自己的 `lib/`、`shared/`。**DeerFlow 迁移脚本（`migrate_hermes_water_resources.py`）即此路线**。优点：`Path(__file__).parent / 'lib'` 天然成立、解析简单；缺点：6 个 skill × (lib+shared) 多份副本、sync 后一致性难维护（与专利 `fusion.py`/`planner.py` 的单一事实源冲突）。

> **本设计的抉择：以路线 S（兄弟目录）为权威源**，因为它是仓库的真实结构，且专利核心（`lib/fusion.py` 单份）依赖它。路线 E 仅作为 DeerFlow 的「可选部署态」，由迁移脚本按需生成，**不进 Git 主干**。通过一个**双布局自适应的解析器**，让一份源码同时支撑两条路线。

---

## 3. 问题诊断（water-situation 现状）

### 3.1 仓库真实结构（路线 S）

```
skills/
├── water-situation/
│   ├── SKILL.md
│   └── references/            ← 7 个 .md
├── rainfall/, water-quality/, ...   ← 其他 skill（各带自己的 references/）
├── lib/                       ← 共享 Python：db.py, fusion.py, planner.py
├── shared/                    ← 共享文档：db_connection.md, sql_*.md, ...
└── scripts/                   ← 评测/门控脚本（仅离线运行，不进 LLM 运行时）
```

`lib/`、`shared/`、`scripts/` 是 `water-situation/` 的**兄弟**，不是子目录。

### 3.2 三处具体错误

**Bug 1 — `lib/db.py:6` 的 docstring 示例自相矛盾（broken）**
```python
# db.py 自己就在 lib/ 里，__file__.parent 已经是 lib/
sys.path.insert(0, str(Path(__file__).parent / 'lib'))   # = lib/lib ❌ 不存在
```
LLM 照抄此示例必失败。

**Bug 2 — `lib/fusion.py:11`、`lib/planner.py:8` 硬编码 stale 路径（broken）**
```python
sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')   # ❌ 运行时不存在
```
CLAUDE.md:73 已承认此路径 stale。Hermes 实际副本在 `/root/.hermes/skills/water-resources/lib`，DeerFlow 在 `/mnt/skills/lib`。

**Bug 3 — `water-situation/SKILL.md:48` 把 Bug 1 当规范推广（broken）**
```markdown
- **db 模块路径:** 使用 `lib/db.py` 助手模块，标准导入方式为
  `sys.path.insert(0, str(Path(__file__).parent / 'lib'))`（相对路径，符合 skill 规范）。
```
该写法仅在「脚本文件物理位于含 `lib/` 子目录的目录内」时成立——即路线 E。在路线 S 下，LLM 生成的暂存脚本位于 workspace，`__file__.parent/'lib'` 指向 workspace/lib，必然落空。

> **对照（正确的相对路径写法已存在于本仓库）**：`scripts/verify_knowledge.py:20`、`run_gate.py:29`、`autoresearch.py:563`、`evaluate_skills.py:656` 都用 `Path(__file__).resolve().parent.parent / 'lib'`（`.parent.parent`：`scripts/` → `skills/` → `lib/`）。**这些离线脚本能跑通，恰恰因为它们从真实绝对路径执行、且 `scripts/` 与 `lib/` 是兄弟**。但 LLM 运行时生成的暂存脚本不满足「从真实 skill 路径执行」，所以不能直接复用此模式。

### 3.3 根因归纳

| 现象 | 根因 |
|------|------|
| LLM 找不到 `db` 模块 | `__file__` 在 workspace/暂存目录，不是 skill_dir；且 `lib/` 是兄弟而非子目录 |
| `shared/` 引用在 Hermes 失败 | `skill_view` 禁止 `..`，`shared/` 在 skill_dir 父级 |
| 同一份 SKILL.md 难以同时适配两平台 | 两平台路径模型不同（虚拟 vs 绝对），且布局假设（嵌套 vs 兄弟）未统一 |

---

## 4. 设计方案

### 4.1 三层架构（核心思想）

把「文件引用」拆成三层，各司其职，互不耦合：

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1  AUTHORING（作者层）                            │
│  SKILL.md 里只写「逻辑相对路径」：                          │
│    references/schema.md   shared/db_connection.md   lib/db.py │
│  ✗ 无绝对路径  ✗ 无平台 token（${HERMES_SKILL_DIR} 不进 prose）│
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│  Layer 2  INJECTION（注入层，平台原生）                    │
│  DeerFlow system prompt:  Skills at /mnt/skills           │
│  Hermes system prompt:    [Skill directory: /abs/skill_dir]│
│  → LLM 据此把「逻辑相对路径」翻译成「平台绝对/虚拟路径」      │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│  Layer 3  RESOLUTION（运行时解析层）                       │
│  部署设单一根环境变量 WATER_RESOURCES_ROOT（指向 skills/）  │
│  运行期：lib/shared 由 $ROOT 派生；bootstrap.py 兜底候选   │
│  → 灵感：与 ${CLAUDE_PLUGIN_ROOT} 同构（一个根变量 + 派生）  │
└─────────────────────────────────────────────────────────┘
```

> **为什么用环境变量（而非候选路径硬编码）作为主路径**：
> 1. **真正平台无关**——SKILL.md 与导入片段里**零**平台字面量（无 `/mnt/skills`、`~/.hermes`），完全靠部署注入。候选根方案仍把这三条路径写进了 LLM 粘贴的代码块。
> 2. **更灵活**——部署路径任意变（换机器、换容器、换挂载点），只改一个环境变量，skill 源码一行不动。
> 3. **与现有约定一致**——`SL323_DB_*` 已用环境变量做配置；`WATER_RESOURCES_ROOT` 沿用同一范式；并与你给的 `${CLAUDE_PLUGIN_ROOT}`、Hermes 的 `${HERMES_SKILL_DIR}` 同构（都是「一个根变量 + 相对派生」）。
> 4. **导入片段最简**——从 6 行候选循环降到 2 行 `os.environ` 读取。

- **Layer 1** 保证「只写一版、无硬编码、符合 skill 规范」。
- **Layer 2** 用两个平台**已有的原生注入**，不需要我们改平台源码。
- **Layer 3** 解决 LLM 暂存脚本里 `__file__` 不可靠的问题——这是两平台共同的痛点。

### 4.2 逻辑相对路径约定（Layer 1 规范）

**所有引用以「skills 根」为基准的逻辑相对路径，不区分平台：**

| 引用对象 | 逻辑相对路径（写入 SKILL.md） |
|---------|-----------------------------|
| 本 skill 的参考文档 | `references/schema.md` |
| 跨 skill 共享文档 | `shared/db_connection.md` |
| 跨 skill 共享库 | `lib/db.py`（Python：`from db import query`） |
| 跨 skill 脚本 | `scripts/xxx.py` |

**SKILL.md 里只用这些 token，绝不出现** `/opt/git/...`、`/root/.hermes/...`、`/mnt/skills/...`、`${HERMES_SKILL_DIR}` 等平台/部署相关字面量。

### 4.3 环境变量契约（Layer 3，核心）

**单一根变量，一切派生：**

| 环境变量 | 含义 | 由谁设置 | 优先级 |
|---------|------|---------|--------|
| `WATER_RESOURCES_ROOT` | 指向 `skills/` 目录（含 `lib/`、`shared/`、各 skill） | **部署层**（DeerFlow sandbox env / Hermes 启动 env / dev `.env`） | 主（必设） |
| `WATER_RESOURCES_LIB` | 直接指向 `lib/`（覆盖 ROOT 派生） | 可选，仅当 lib 与 ROOT 不同构时 | 覆盖 |
| `WATER_RESOURCES_SHARED` | 直接指向 `shared/` | 可选 | 覆盖 |

> **设计要点**：与 `${CLAUDE_PLUGIN_ROOT}` 同构——**一个根变量**，`lib`/`shared` 由 `$ROOT/lib`、`$ROOT/shared` 派生。部署只设 `WATER_RESOURCES_ROOT` 一个变量；`LIB`/`SHARED` 仅在特殊布局（如路线 E 嵌套）下覆盖。

### 4.4 统一解析器 `lib/bootstrap.py`（离线脚本复用）

新增 `lib/bootstrap.py`，供 `scripts/*.py`（从真实路径运行的离线脚本）复用；**优先级：ROOT 环境变量 → 显式覆盖 → 候选根兜底**：

```python
# lib/bootstrap.py
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
```

**为何仍保留候选根兜底**：开发环境或未配置环境变量的临时运行，免去「必须先 export」的摩擦；生产/正式部署则靠环境变量保证确定性。新增部署环境，正式路径改 `WATER_RESOURCES_ROOT`（不动代码），兜底才改 `_KNOWN_ROOTS`。

### 4.5 SKILL.md 中的「标准导入片段」（LLM 契约）

在 SKILL.md 的 `Prerequisites` 节，给出**唯一权威的导入片段**，要求 LLM 照抄——**仅依赖环境变量，无任何平台字面量**：

```python
# 标准导入（双平台通用）—— lib/ 由部署环境变量定位，__file__ 不可靠勿用
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi   # 只读查询，30s 超时，返回 list[dict]
```

> **对比候选根方案**：本片段 2 行，无 `/mnt/skills`、`~/.hermes` 等字面量；平台差异完全收敛到「部署设 `WATER_RESOURCES_ROOT`」一处。LLM 暂存脚本无法 `import` 到 `lib/bootstrap.py`（先有鸡先有蛋），故运行时用内联片段；离线脚本用 `bootstrap.py`。

---

## 5. water-situation 改造范例（Before / After）

### 5.1 SKILL.md 改动

**改动点 A — `Prerequisites` 节（行 32-37 区域）**

Before:
```markdown
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），
  自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
```

After（新增「标准导入片段」与「路径约定」子节）:
```markdown
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），
  自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**

### 文件引用约定（双平台通用）

本 skill 通过「逻辑相对路径」引用共享资源，真实路径由**部署环境变量 `WATER_RESOURCES_ROOT`**（指向 skills/）派生：

| 引用 | 逻辑路径 | 运行时真实路径（两平台统一） |
|------|---------|---------------------------|
| 共享库 | `lib/db.py` | `$WATER_RESOURCES_ROOT/lib/db.py` |
| 共享文档 | `shared/db_connection.md` | `$WATER_RESOURCES_ROOT/shared/db_connection.md` |
| 本 skill 参考 | `references/schema.md` | （skill_dir 内，由平台注入的 skill 目录决定） |

> `WATER_RESOURCES_ROOT` 由部署层设置：DeerFlow 指向 `/mnt/skills`，Hermes 指向 `~/.hermes/skills/water-resources`，开发指向仓库 `…/skills`。

**标准导入片段**（生成查询代码时照抄，`__file__` 不可靠，勿用）：
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi
```
```

**改动点 B — `Pitfalls` 节第 48 行（删除错误规范）**

Before:
```markdown
- **db 模块路径:** 使用 `lib/db.py` 助手模块，标准导入方式为
  `sys.path.insert(0, str(Path(__file__).parent / 'lib'))`（相对路径，符合 skill 规范）。
```

After（移除自相矛盾的 `__file__` 写法，指向标准片段）:
```markdown
- **db 模块路径:** 见上方「标准导入片段」。⚠️ 不要用 `Path(__file__).parent / 'lib'`——
  LLM 生成的暂存脚本 `__file__` 在 workspace，lib/ 是 skill 的兄弟目录而非子目录，该写法会定位到不存在的路径。
```

### 5.2 `lib/db.py` 改动

Before（行 1-12，docstring 给出错误示例）:
```python
"""Shared DB helper for water-resources skills.

Usage:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent / 'lib'))
    from db import query, query_multi
    ...
"""
```

After（docstring 改为指向标准片段 + bootstrap）:
```python
"""Shared DB helper for water-resources skills.

Usage (LLM-generated runtime script — __file__ unreliable, use the
ROOT env-var snippet documented in SKILL.md "标准导入片段"):

    import os, sys
    sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
    from db import query, query_multi

Usage (offline scripts under scripts/, run from real path — uses bootstrap
resolver which adds env-var override + candidate fallback):

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lib'))
    from bootstrap import locate_lib, locate_shared
    from db import query
"""
```

### 5.3 `lib/fusion.py` / `lib/planner.py` 改动

Before（stale 硬编码）:
```python
sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')
```

After（兄弟布局的 `.parent.parent`，或直接 import，因为它们本身就在 lib/ 内无需再 insert）:
```python
# fusion.py / planner.py 已位于 lib/ 内，同级 import 无需 sys.path 操作
from db import query          # 同目录直接 import
# （删除所有 sys.path.insert 行）
```

> `fusion.py`/`planner.py` 与 `db.py` 同在 `lib/`，Python 同目录模块直接 `import db` 即可，**无需任何 sys.path 操作**。删除硬编码行即可根除 Bug 2。

### 5.4 新增 `lib/bootstrap.py`

见 §4.3 完整代码。供 `scripts/*.py` 离线脚本统一调用：
```python
# scripts/xxx.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lib'))
from bootstrap import locate_shared   # 复用解析逻辑
```

### 5.5 `shared/db_connection.md` 改动

将「路径说明」节（行 94-107）的「标准写法 `Path(__file__).parent / 'lib'`」替换为与 SKILL.md 一致的环境变量标准片段说明，并标注「该写法仅适用于离线脚本（从真实路径运行）；LLM 运行时请用 `WATER_RESOURCES_ROOT` 环境变量片段」。

---

## 6. 双平台部署配方

### 6.1 DeerFlow

1. **config.yaml**（已就绪，决定挂载点）:
   ```yaml
   skills:
     path: /opt/git/water-resources-skills/skills
     container_path: /mnt/skills
   ```
2. **【关键】设根环境变量**——在 sandbox 启动环境注入，使标准片段的 `os.environ['WATER_RESOURCES_ROOT']` 命中:
   ```bash
   export WATER_RESOURCES_ROOT=/mnt/skills
   ```
   注入方式：DeerFlow 启动脚本 / systemd `Environment=` / Docker `ENV`（容器内值即虚拟根 `/mnt/skills`）。设此一个变量后，`lib`/`shared` 全部由 `$ROOT/lib`、`$ROOT/shared` 派生，标准片段 2 行即可工作。
3. **布局选择**：保持路线 S（兄弟目录）即可，**不必**跑迁移脚本生成路线 E 的自包含副本。解析器已兼容两者；若某 skill 必须离线分发给无网络环境，再单独迁移该 skill。

### 6.2 Hermes Agent

1. **让 hermes 看到本仓库**（三选一）:
   - **(推荐) external_dirs**——在 `~/.hermes/config.yaml`:
     ```yaml
     skills:
       external_dirs:
         - /opt/git/water-resources-skills/skills
     ```
     零拷贝、改即生效、git 单一源。
   - **手动 sync**——`rsync -a /opt/git/water-resources-skills/skills/water-resources/ ~/.hermes/skills/water-resources/`（需每次改完手动跑）。
   - **软链接**——`ln -s /opt/git/water-resources-skills/skills ~/.hermes/skills/water-resources`（注意 hermes 的 `os.walk(followlinks=True)` 支持，但词法路径可信根校验见 Hermes 分析 §5.2，需保证链接目标在信任根内）。
2. **【关键】设根环境变量**——Hermes 启动环境注入:
   ```bash
   export WATER_RESOURCES_ROOT=/root/.hermes/skills/water-resources   # 或 external_dirs 指向的路径
   ```
   注入方式：启动 hermes 的 shell profile（`~/.bashrc`）/ systemd / supervisor env。设后标准片段无需区分平台。
3. **shared/ 跨 skill 引用**——Hermes 的 `skill_view` 禁 `..`，无法读兄弟 `shared/`。对策:
   - **(推荐) 终端读取绝对路径**：SKILL.md 文案提示「`shared/db_connection.md` 在根下，用终端 `cat $WATER_RESOURCES_ROOT/shared/db_connection.md`」。LLM 从环境变量拿到确定性绝对路径，不靠推断。
   - **(可选) `${HERMES_SKILL_DIR}`**：在 SKILL.md 写 `${HERMES_SKILL_DIR}/../shared/db_connection.md`，加载时被替换为绝对路径。**注意**：此 token 是 Hermes 专属，违反 §4.2「prose 无平台 token」原则，仅在「Hermes-only 段落」内使用并明确标注。

### 6.3 开发环境

仓库根 `.env`（已 gitignore）:
```bash
SL323_DB_PASSWORD=...
WATER_RESOURCES_ROOT=/opt/git/water-resources-skills/skills
```
设 `WATER_RESOURCES_ROOT` 后，本地 `python3 scripts/*.py` 与 LLM 片段走同一路径解析，无需 `WATER_RESOURCES_LIB` 额外覆盖。

---

## 7. 改造步骤（执行清单）

> 参考 spec-superflow 的结构：Pre-Flight → 执行 → 验证 → 归档。

### Pre-Flight
- [ ] 确认仓库为路线 S 布局（`ls skills/{lib,shared,scripts}` 存在且与 skill 同级）
- [ ] 备份现状：`scripts/run_gate.py` 的 baseline 机制可复用（备份 SKILL.md + references + shared）
- [ ] 确认 DeerFlow `config.yaml`、Hermes `external_dirs` 配置正确
- [ ] **确认两平台根环境变量可注入**：DeerFlow sandbox env、Hermes 启动 env 各自能设 `WATER_RESOURCES_ROOT`（这是整个方案的硬前提）

### Step 1 — 修复 lib 内部错误（Bug 2）
- [ ] `lib/fusion.py`：删除 `sys.path.insert('/opt/git/hermes-agent/...')`，改 `from db import query`
- [ ] `lib/planner.py`：同上
- [ ] `lib/db.py`：docstring 改为环境变量片段（§5.2）

### Step 2 — 新增解析器
- [ ] 创建 `lib/bootstrap.py`（§4.4）——环境变量优先 + 候选兜底

### Step 3 — 改造 water-situation（范例）
- [ ] SKILL.md `Prerequisites`：新增「文件引用约定 + 环境变量标准片段」（§5.1-A）
- [ ] SKILL.md `Pitfalls:48`：删除错误 `__file__` 规范（§5.1-B）
- [ ] `shared/db_connection.md`：同步路径说明（§5.5）

### Step 4 — 推广到其他 skill（批量）
- [ ] 其余 5 个 data skill + water-fusion：套用同一「环境变量片段 + Pitfalls 修正」模板
- [ ] 用 §8.1 静态检查脚本扫描残留，逐一替换

### Step 5 — 部署环境变量（双平台）
- [ ] DeerFlow：sandbox 启动注入 `WATER_RESOURCES_ROOT=/mnt/skills`
- [ ] Hermes：启动 env 注入 `WATER_RESOURCES_ROOT=<挂载路径>`
- [ ] 开发：仓库 `.env` 写 `WATER_RESOURCES_ROOT=<repo>/skills`

### Step 6 — 双平台验证（见 §8）

### Step 7 — 归档
- [ ] 提交：`refactor(skill): 双平台文件引用统一（WATER_RESOURCES_ROOT 环境变量 + bootstrap）`
- [ ] 更新 `CLAUDE.md` 的「Critical conventions」节，把 stale 路径警告替换为本设计链接

---

## 8. 验证门禁（双平台都必须通过）

### 8.1 静态检查
```bash
# 1. SKILL.md / 文档无平台路径字面量（环境变量方案后应彻底消失）
grep -rn "/opt/git/hermes-agent\|/root/.hermes\|/mnt/skills" skills/ \
  --include="*.md" | grep -v deerflow-skill-path-analysis.md
# 期望：0 命中（仅历史分析文档可保留）

# 2. SKILL.md 片段应引用 WATER_RESOURCES_ROOT，而非硬编码候选根
grep -rLn "WATER_RESOURCES_ROOT" skills/*/SKILL.md
# 期望：0 命中（每个 SKILL.md 都含该环境变量片段）

# 3. 无错误 __file__ 模式（lib 同级 import 除外）
grep -rn "Path(__file__).parent / 'lib'" skills/ --include="*.py" --include="*.md"
# 期望：0 命中（lib 内模块用 from db import；离线脚本用 .parent.parent）

# 4. 无 stale hermes 绝对路径
grep -rn "/opt/git/hermes-agent/skills/water-resources/lib" skills/
# 期望：0 命中
```

### 8.2 DeerFlow 运行验证
```bash
# 0. 确认根环境变量已注入沙箱
echo "$WATER_RESOURCES_ROOT"   # 期望：/mnt/skills

# 1. SKILL.md 能被 describe_skill 发现
# 2. read_file('$WATER_RESOURCES_ROOT/lib/db.py') 能读到
# 3. LLM 生成的查询代码能成功 from db import query 并执行一条 SELECT
# 4. read_file('$WATER_RESOURCES_ROOT/shared/db_connection.md') 能读到
```

### 8.3 Hermes Agent 运行验证
```bash
echo "$WATER_RESOURCES_ROOT"   # 期望：/root/.hermes/skills/water-resources
hermes -s water-situation -z "古运河有哪些水位测站"
# 期望：
# - skill 正常激活（[Skill directory: ...] 注入成功）
# - 生成 SQL 并执行成功（说明 $WATER_RESOURCES_ROOT/lib 被正确定位）
# - 不出现 ModuleNotFoundError: db / KeyError: WATER_RESOURCES_ROOT

# 验证 shared 跨 skill 读取（终端 + 环境变量）
hermes -s water-situation -z "查询时引用 shared/sql_safety_rules.md 的规则"
# 期望：LLM 用终端 cat $WATER_RESOURCES_ROOT/shared/sql_safety_rules.md 成功读取
```

### 8.4 离线脚本回归
```bash
cd skills
python3 scripts/evaluate_skills.py --skill water-situation --level L1 --range 1-5 --dry-run
python3 scripts/run_gate.py   # baseline diff，确保改动未引入回归
```

---

## 9. Guardrails（护栏）

- **环境变量是契约，不是可选**：`WATER_RESOURCES_ROOT` 是部署层的硬前提。两平台都必须在启动环境注入它；未注入则标准片段抛 `KeyError`（这是有意为之的 fail-fast，优于静默猜路径）。
- **不要**把路线 E（自包含嵌入）的产物提交进 Git——它是 DeerFlow 迁移脚本的**生成物**，源是路线 S。提交会造成 `fusion.py`/`planner.py` 多份漂移，破坏专利单一事实源。
- **不要**在 SKILL.md 里写 `/mnt/skills`、`/root/.hermes`、`${HERMES_SKILL_DIR}` 等平台/部署字面量——标准片段只引用 `WATER_RESOURCES_ROOT`；`${HERMES_SKILL_DIR}` 仅允许在显式标注的「Hermes-only 段落」。
- **不要**用 `Path(__file__).parent / 'lib'` 教 LLM——它在 workspace/暂存脚本下必失效。LLM 运行时一律用环境变量片段；离线脚本用 `.parent.parent / 'lib'` + bootstrap。
- **不要**让 `lib/fusion.py`、`lib/planner.py` 自行 `sys.path.insert`——它们已在 lib/ 内，直接 `from db import query`。
- 新增部署环境：**首选**改部署的 `WATER_RESOURCES_ROOT` 注入值（零代码改动）；仅当无法注入环境变量时，才动 `bootstrap.py` 的 `_KNOWN_ROOTS` 兜底常量。
- 修改后**必须**跑 §8 全部门禁；DeerFlow 与 Hermes 任一失败即未完成。

---

## 10. 设计权衡与遗留问题

| 决策 | 选择 | 理由 | 代价 |
|------|------|------|------|
| 权威布局 | 路线 S（兄弟目录） | 仓库真实结构 + 专利单源依赖 | Hermes 跨 skill 引用需终端绕行 skill_view |
| 路径主机制 | **环境变量 `WATER_RESOURCES_ROOT`** | 与 `${CLAUDE_PLUGIN_ROOT}` 同构；零平台字面量；部署改路径不动代码 | 部署必须注入该变量（fail-fast） |
| 路径兜底 | bootstrap.py 候选根 + 显式覆盖 | 未配环境变量时的便利；离线脚本复用 | `_KNOWN_ROOTS` 需随新环境维护（次要） |
| LLM 导入 | 内联环境变量片段（2 行） | 暂存脚本无法 import bootstrap（先有鸡先有蛋）；最简 | 片段需与 bootstrap 语义保持一致（人工同步） |
| Hermes shared 读取 | 终端 cat `$WATER_RESOURCES_ROOT/shared/...` | skill_view 禁 `..`，无他法；环境变量给确定绝对路径 | 无（不依赖 LLM 路径推断） |
| DeerFlow 布局 | 保持路线 S，不强制迁移 E | 解析器双布局兼容，避免副本漂移 | 若需离线分发单 skill，仍要跑迁移脚本 |

### 遗留问题（需后续决策）
1. **`scripts/` 目录**：评测/门控脚本（`evaluate_skills.py`、`run_gate.py` 等）目前用 `.parent.parent` 正确，但它们**不是 skill 运行时的一部分**（不进 LLM 上下文）。是否在 SKILL.md 里引用它们？建议**不引用**，保持 skill 运行时精简；脚本能力在 `CLAUDE.md` 文档化。
2. **`build-dashboard`/`create-viz`/`data-context-extractor`**：这三个较新 skill 当前无 `references/`，CLAUDE.md 标注「untracked」。本设计的标准片段同样适用，但需确认它们是否需要 lib/（目前看是纯 viz skill，可能不需要 DB）。
3. **环境变量命名**：主变量 `WATER_RESOURCES_ROOT` 与现有 `SL323_DB_*` 前缀不同（前者定位仓库、后者定位数据库），语义分层合理，建议保持。覆盖变量 `WATER_RESOURCES_LIB`/`_SHARED` 仅特殊布局用，命名同样保持 `WATER_RESOURCES_*` 前缀。

---

## 11. 总结

本设计的核心是**三层分离 + 环境变量根 + 双布局自适应解析器**：

1. **作者层**只写逻辑相对路径（`lib/db.py`、`shared/x.md`、`references/x.md`），符合 skill 规范，无硬编码、无平台字面量。
2. **注入层**复用两平台原生机制（DeerFlow `/mnt/skills`、Hermes `[Skill directory]`），不改平台源码；**两平台各自在启动环境注入 `WATER_RESOURCES_ROOT`**。
3. **解析层** LLM 运行时用 2 行环境变量片段（`sys.path.insert(0, $ROOT/lib)`）；离线脚本用 `lib/bootstrap.py`（环境变量优先 + 候选兜底）；`lib`/`shared`/`references` 三类引用由此统一解析，适配兄弟/嵌套两种布局与虚拟/绝对两种路径模型。

环境变量方案相比候选根硬编码的优势（采纳你的建议）：**真正平台无关、部署零代码改动、与 `SL323_DB_*` 及 `${CLAUDE_PLUGIN_ROOT}` 范式一致、LLM 片段从 6 行降到 2 行**。

通过修复 3 处具体 Bug、新增 1 个解析器、约定 1 个根环境变量、统一 1 份导入契约，`water-situation`（及同类 skill）即可在 DeerFlow 与 Hermes Agent 上零平台分支地正确引用所有文件。

**落地优先级**：Step 1-3（修 lib + bootstrap + water-situation 范例）→ Step 5（两平台注入 `WATER_RESOURCES_ROOT`）→ §8 验证 → Step 4 批量推广 → 归档。
