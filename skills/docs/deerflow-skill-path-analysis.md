# DeerFlow Skill 路径解析机制深度分析

**分析时间**: 2026-07-14
**分析对象**: /opt/git/deer-flow/backend/packages/harness/deerflow/

---

## 目录

1. [架构概览](#架构概览)
2. [路径解析完整流程](#路径解析完整流程)
3. [关键组件源码分析](#关键组件源码分析)
4. [LLM 如何读取 Skill 文件](#llm-如何读取-skill-文件)
5. [路径定位机制](#路径定位机制)
6. [常见问题与解决方案](#常见问题与解决方案)

---

## 架构概览

### 1.1 三层路径结构

```
┌─────────────────────────────────────────────────────────┐
│                      LLM / Agent                          │
│  看到的路径: /mnt/skills/public/water-situation/         │
└───────────────────────┬─────────────────────────────────┘
                        │ 虚拟容器路径 (container_path)
┌───────────────────────▼─────────────────────────────────┐
│              DeerFlow PathMapping                        │
│  映射: /mnt/skills → /opt/git/water-resources-skills    │
└───────────────────────┬─────────────────────────────────┘
                        │ Host 实际路径 (host_path)
┌───────────────────────▼─────────────────────────────────┐
│              Git 仓库实际文件                             │
│  /opt/git/water-resources-skills/skills/                │
│  ├── water-situation/SKILL.md                           │
│  ├── lib/db.py                                           │
│  └── references/water_classification.md                  │
└─────────────────────────────────────────────────────────┘
```

### 1.2 关键组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **LocalSkillStorage** | `skills/storage/local_skill_storage.py` | 管理本地文件系统的 skill 存储 |
| **SkillParser** | `skills/parser.py` | 解析 SKILL.md 的 YAML frontmatter |
| **SkillCatalog** | `skills/catalog.py` | Skill 搜索和发现 |
| **SkillActivationMiddleware** | `agents/middlewares/skill_activation_middleware.py` | Slash 激活 skill |
| **read_file_tool** | `sandbox/tools.py` | 文件读取工具（含路径解析） |
| **Prompt** | `agents/lead_agent/prompt.py` | LLM system prompt 生成 |

---

## 路径解析完整流程

### 2.1 初始化阶段

#### Step 1: 配置加载

```yaml
# config.yaml
skills:
  path: /opt/git/water-resources-skills/skills  # host_path
  container_path: /mnt/skills  # 虚拟路径
```

**源码**: `deerflow/config/skills_config.py`
```python
def get_skills_path(self) -> Path:
    """返回 host_path: /opt/git/water-resources-skills/skills"""
    return Path(self.path)
```

#### Step 2: LocalSkillStorage 初始化

**源码**: `skills/storage/local_skill_storage.py:39-52`
```python
class LocalSkillStorage(SkillStorage):
    def __init__(self, host_path=None, container_path=DEFAULT_SKILLS_CONTAINER_PATH):
        if host_path is None:
            config = get_app_config()
            self._host_root = config.skills.get_skills_path()
        else:
            self._host_root = resolve_path(host_path)
        self._container_root = container_path
```

**结果**：
- `_host_root` = `/opt/git/water-resources-skills/skills`
- `_container_root` = `/mnt/skills`

#### Step 3: Skill 发现

**源码**: `skills/storage/local_skill_storage.py:68-79`
```python
def _iter_skill_files(self):
    if not self._host_root.exists():
        return
    for category in SkillCategory:
        category_path = self._host_root / category.value
        # e.g., /opt/git/water-resources-skills/skills/public
        for current_root, dir_names, file_names in os.walk(category_path, followlinks=True):
            if SKILL_MD_FILE not in file_names:
                continue
            yield category, category_path, Path(current_root) / SKILL_MD_FILE
```

**遍历结果**：
```
/opt/git/water-resources-skills/skills/public/water-situation/SKILL.md
/opt/git/water-resources-skills/skills/rainfall/SKILL.md
...
```

#### Step 4: Skill 对象创建

**源码**: `skills/parser.py:122-207`
```python
def parse_skill_file(skill_file: Path, category, relative_path=None):
    content = skill_file.read_text(encoding="utf-8")
    # 解析 YAML frontmatter
    front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    metadata = yaml.safe_load(front_matter_match.group(1))

    return Skill(
        name=metadata['name'],  # 'water-situation'
        description=metadata['description'],
        skill_dir=skill_file.parent,  # /opt/git/.../water-situation/
        skill_file=skill_file,  # /opt/git/.../water-situation/SKILL.md
        relative_path=relative_path or Path(skill_file.parent.name),
        category=category,
    )
```

---

## LLM 如何读取 Skill 文件

### 3.1 System Prompt 中的路径信息

**源码**: `agents/lead_agent/prompt.py:162-180`
```python
def get_skill_index_prompt_section(...):
    return f"""<skill_system>
You have access to skills that provide optimized workflows.

**Skills are located at:** {container_base_path}
<skill_index>
{names}
</skill_index>
</skill_system>"""
```

**LLM 看到的 Prompt**：
```
<skill_system>
Skills are located at: /mnt/skills
<skill_index>
water-situation, rainfall, ...
</skill_index>
</skill_system>
```

### 3.2 describe_skill 工具

**源码**: `skills/describe.py:62-96`
```python
@tool
def describe_skill(name: str, tool_call_id) -> Command:
    """Fetch usage metadata for installed skills so you can decide
    whether to load the SKILL.md via read_file."""
    matched = catalog.search(name)
    if matched:
        content = _render_skill_metadata(matched, container_base_path)
        # 返回 skill 位置
        # Location: /mnt/skills/public/water-situation/SKILL.md
```

**LLM 调用流程**：
```
User: "查询古运河水位"
  → LLM: describe_skill("water-situation")
  → DeerFlow: 返回 Location: /mnt/skills/public/water-situation/SKILL.md
  → LLM: read_file("/mnt/skills/public/water-situation/SKILL.md")
  → DeerFlow: 读取 /opt/git/water-resources-skills/skills/water-situation/SKILL.md
  → LLM: 看到 SKILL.md 内容
```

### 3.3 read_file 工具与路径解析

**源码**: `sandbox/tools.py`

#### Step 1: 路径验证

```python
@tool("read_file")
def read_file_tool(runtime, description, path, start_line=None, end_line=None):
    sandbox = ensure_sandbox_initialized(runtime)
    if is_local_sandbox(runtime):
        thread_data = get_thread_data(runtime)
        validate_local_tool_path(path, thread_data, read_only=True)

        # 关键: 识别 skill 路径并解析
        if _is_skills_path(path):
            path = _resolve_skills_path(path)
```

#### Step 2: 识别 Skill 路径

```python
def _is_skills_path(path: str) -> bool:
    """检查路径是否在 skill 容器下"""
    skills_prefix = _get_skills_container_path()  # "/mnt/skills"
    return path == skills_prefix or path.startswith(f"{skills_prefix}/")
```

#### Step 3: 解析到 Host 路径

```python
def _resolve_skills_path(path: str) -> str:
    """将虚拟路径解析为实际 host 路径"""
    skills_container = _get_skills_container_path()  # "/mnt/skills"
    skills_host = _get_skills_host_path()  # "/opt/git/water-resources-skills/skills"

    # 替换前缀: /mnt/skills → /opt/git/water-resources-skills/skills
    relative = path[len(skills_container):].lstrip("/")
    # "public/water-situation/SKILL.md"

    # 构建实际路径（考虑 user-scoped custom skills）
    if category == "custom":
        # 自定义 skill 使用 per-user 路径
        user_custom_dir = _get_user_custom_dir(user_id)
        return str(Path(user_custom_dir) / relative)
    else:
        # Public skill 直接拼接
        return str(Path(skills_host) / relative)
```

**路径映射示例**：
```
/mnt/skills/public/water-situation/SKILL.md
  → /opt/git/water-resources-skills/skills/public/water-situation/SKILL.md

/mnt/skills/public/water-situation/references/water_classification.md
  → /opt/git/water-resources-skills/skills/public/water-situation/references/water_classification.md
```

---

## 路径定位机制

### 4.1 虚拟路径 vs Host 路径

| 视角 | 路径格式 | 示例 |
|------|---------|------|
| **LLM 看到的** | `/mnt/skills/public/<skill>/<file>` | `/mnt/skills/public/water-situation/SKILL.md` |
| **实际文件系统** | `/opt/git/water-resources-skills/skills/<category>/<skill>/<file>` | `/opt/git/water-resources-skills/skills/public/water-situation/SKILL.md` |

### 4.2 Skill 内部路径

**相对路径关系**：
```
SKILL.md (主文件)
  ├─ references/water_classification.md
  ├─ references/elevation_datum.md
  ├─ lib/db.py
  └─ shared/db_connection.md
```

**LLM 如何构建 references 文件路径**：

1. **从 SKILL.md 提取 skill 目录**：
   ```
   /mnt/skills/public/water-situation/SKILL.md
   → skill_dir = /mnt/skills/public/water-situation/
   ```

2. **LLM 构建 references 文件路径**：
   ```
   skill_dir + "references/water_classification.md"
   = /mnt/skills/public/water-situation/references/water_classification.md
   ```

3. ** DeerFlow 解析为实际路径**：
   ```
   /opt/git/water-resources-skills/skills/water-situation/references/water_classification.md
   ```

### 4.3 Python 代码中的路径

**问题**: LLM 生成 Python 代码时，`__file__` 指向哪里？

**答案**: **不确定，依赖于执行方式**。

#### 执行方式 1: 脚本在 workspace 中

```python
# LLM 生成脚本: /mnt/user-data/workspace/temp_query.py
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
# __file__ = /mnt/user-data/workspace/temp_query.py
# → lib = /mnt/user-data/workspace/lib ❌ 不存在
```

#### 执行方式 2: 脚本在 skill 目录中

```python
# LLM 生成脚本: /mnt/skills/public/water-situation/scripts/temp_query.py
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
# __file__ = /mnt/skills/public/water-situation/scripts/temp_query.py
# → lib = /mnt/skills/public/water-situation/lib ✅ 正确
```

#### 执行方式 3: 通过 bash 执行 Python 代码

```bash
# DeerFlow 自动添加 cd 前缀
cd /mnt/user-data/workspace && python3 << 'PYEOF'
import sys
sys.path.insert(0, '/mnt/skills/public/water-situation/lib')  # ✅ 使用虚拟路径
from db import query
PYEOF
```

---

## 常见问题与解决方案

### 5.1 为什么 `Path(__file__)` 有时不可靠？

**原因**:
- DeerFlow 在 `/mnt/user-data/workspace/` 执行代码
- LLM 生成的临时脚本位于 workspace，不在 skill 目录
- `__file__` 指向 workspace 中的临时文件

**解决方案**:
```python
# 方案1: 使用虚拟路径（推荐）
sys.path.insert(0, '/mnt/skills/public/water-situation/lib')

# 方案2: 确保脚本在 skill 目录中执行
# 通过 bash 工具 cd 到 skill 目录
cd /mnt/skills/public/water-situation && python3 script.py

# 方案3: 使用环境变量
import os
skill_dir = os.environ.get('SKILL_DIR', '/mnt/skills/public/water-situation')
sys.path.insert(0, f'{skill_dir}/lib')
```

### 5.2 如何读取 references 文件？

**正确方式**:
```python
# LLM 使用 read_file 工具
read_file('/mnt/skills/public/water-situation/references/water_classification.md')
```

**错误方式**:
```python
# ❌ 不要假设实际路径
with open('/opt/git/water-resources-skills/skills/water-situation/references/xxx.md') as f:
    # LLM 不知道实际路径
```

### 5.3 PathMapping 如何工作？

**源码**: `sandbox/local/local_sandbox.py`

```python
class LocalSandbox(Sandbox):
    def read_file(self, path: str) -> str:
        # PathMapping 自动映射虚拟路径到 host 路径
        resolved = self._path_mapping.map_path(path)
        # /mnt/skills/public/... → /opt/git/water-resources-skills/skills/...
        return Path(resolved).read_text(encoding="utf-8")
```

**PathMapping 配置**:
```python
# 创建 sandbox 时建立映射
{
    "/mnt/skills": "/opt/git/water-resources-skills/skills",  # skills
    "/mnt/user-data/workspace": "/path/to/workspace",  # workspace
    "/mnt/user-data/uploads": "/path/to/uploads",  # uploads
    "/mnt/user-data/outputs": "/path/to/outputs",  # outputs
}
```

---

## 关键源码位置

### 6.1 Skill 加载

| 功能 | 文件 | 行号 |
|------|------|------|
| Skill 发现 | `skills/storage/local_skill_storage.py` | 68-79 |
| Skill 解析 | `skills/parser.py` | 122-207 |
| Skill 对象 | `skills/types.py` | 38-93 |
| 加载所有 Skills | `skills/storage/skill_storage.py` | 242-279 |

### 6.2 路径解析

| 功能 | 文件 | 行号 |
|------|------|------|
| 获取容器路径 | `sandbox/tools.py` | 108-125 |
| 获取 Host 路径 | `sandbox/tools.py` | 128-150 |
| 识别 Skill 路径 | `sandbox/tools.py` | ~1580 |
| 解析 Skill 路径 | `sandbox/tools.py` | ~1600 |
| PathMapping | `sandbox/local/local_sandbox.py` | 完整类 |

### 6.3 LLM 提示

| 功能 | 文件 | 行号 |
|------|------|------|
| Skill System Prompt | `agents/lead_agent/prompt.py` | 162-180 |
| Working Directory | `agents/lead_agent/prompt.py` | 546-561 |
| describe_skill | `skills/describe.py` | 62-96 |

---

## 总结

### DeerFlow Skill 路径机制的核心要点

1. **两层路径**：
   - 虚拟路径 `/mnt/skills`（LLM 看到）
   - Host 路径 `/opt/git/water-resources-skills/skills`（实际文件）

2. **自动解析**：
   - `read_file` 自动识别 `/mnt/skills` 前缀
   - 自动映射到 host 路径
   - LLM 无需知道实际路径

3. **Skill 内部引用**：
   - LLM 应该基于虚拟路径构建引用
   - 例如：`/mnt/skills/public/water-situation/references/xxx.md`
   - DeerFlow 自动解析

4. **Python 代码中的路径**：
   - **问题**: `__file__` 不可靠
   - **解决**: 使用虚拟路径 `/mnt/skills/public/<skill>/lib`
   - **前提**: 代码在 skill 目录中执行或 bash 先 cd 到 skill 目录

5. **软链接的作用**：
   - DeerFlow 使用软链接同步 Git 仓库
   - `/opt/git/deer-flow/skills/public/water-situation` → Git 仓库
   - 配置中的 `host_path` 可直接指向 DeerFlow 的软链接目录

---

**维护说明**: 本文档基于 DeerFlow commit 3a7572e 分析，如架构变动需更新。
