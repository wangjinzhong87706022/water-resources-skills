---
name: chart-visualization
description: This skill should be used when the user wants to visualize data. It intelligently selects the most suitable chart type from 26 available options, extracts parameters based on detailed specifications, and generates a chart image using a JavaScript script.
compatibility:
  nodejs: ">=18.0.0"
---

# Chart Visualization Skill

This skill provides a comprehensive workflow for transforming data into visual charts. It handles chart selection, parameter extraction, and image generation.

## Workflow

To visualize data, follow these steps:

### 1. Intelligent Chart Selection
Analyze the user's data features to determine the most appropriate chart type. Use the following guidelines (and consult `references/` for detailed specs):

- **Time Series**: Use `generate_line_chart` (trends) or `generate_area_chart` (accumulated trends). Use `generate_dual_axes_chart` for two different scales.
- **Comparisons**: Use `generate_bar_chart` (categorical) or `generate_column_chart`. Use `generate_histogram_chart` for frequency distributions.
- **Part-to-Whole**: Use `generate_pie_chart` or `generate_treemap_chart` (hierarchical).
- **Relationships & Flow**: Use `generate_scatter_chart` (correlation), `generate_sankey_chart` (flow), or `generate_venn_chart` (overlap).
- **Maps**: Use `generate_district_map` (regions), `generate_pin_map` (points), or `generate_path_map` (routes).
- **Hierarchies & Trees**: Use `generate_organization_chart` or `generate_mind_map`.
- **Specialized**:
    - `generate_radar_chart`: Multi-dimensional comparison.
    - `generate_funnel_chart`: Process stages.
    - `generate_liquid_chart`: Percentage/Progress.
    - `generate_word_cloud_chart`: Text frequency.
    - `generate_boxplot_chart` or `generate_violin_chart`: Statistical distribution.
    - `generate_network_graph`: Complex node-edge relationships.
    - `generate_fishbone_diagram`: Cause-effect analysis.
    - `generate_flow_diagram`: Process flow.
    - `generate_spreadsheet`: Tabular data or pivot tables for structured data display and cross-tabulation.

### 2. Parameter Extraction
Once a chart type is selected, read the corresponding file in the `references/` directory (e.g., `references/generate_line_chart.md`) to identify the required and optional fields.
Extract the data from the user's input and map it to the expected `args` format.

### 3. Chart Generation
Invoke the `scripts/generate.js` script with a JSON payload.

**Payload Format:**
```json
{
  "tool": "generate_chart_type_name",
  "args": {
    "data": [...],
    "title": "...",
    "theme": "...",
    "style": { ... }
  }
}
```

**Execution Command:**
```bash
node ./scripts/generate.js '<payload_json>'
```

> **⚠️ 本地化规则（sandbox 环境，高频失败）：数据点 > 20 或 payload 含中文/换行时，禁止内联 JSON，必须先落文件再传路径。** 内联模式 `node generate.js '<长JSON>'` 在 sandbox bash 里，长 payload（中文 + 多行 + 多数据点）会被单引号转义拆分破坏，`generate.js` 走 `JSON.parse(arg)` 时报 `Error parsing spec`、退出码 1（实测 120 个数据点的水位趋势图因此连失败 2 次，重试到第 3 次改用文件才出图，白烧 ~3 分钟）。`generate.js` 内部用 `fs.existsSync(arg)` 判别——**传文件路径会自动走文件分支**，正确做法：
> ```bash
> cat > /mnt/user-data/workspace/chart_payload.json << 'PAYLOAD'
> { "tool": "generate_line_chart", "args": { "title": "...", "data": [...] } }
> PAYLOAD
> node ./scripts/generate.js /mnt/user-data/workspace/chart_payload.json
> ```
> 仅当 payload 极短（< 20 数据点、纯 ASCII）时才允许内联 `node ./scripts/generate.js '<json>'`。

### 4. Result Return
The script will output the URL of the generated chart image.
Return the following to the user:
- The image URL.
- The complete `args` (specification) used for generation.

## Reference Material
Detailed specifications for each chart type are located in the `references/` directory. Consult these files to ensure the `args` passed to the script match the expected schema.

## License

This `SKILL.md` is provided by [antvis/chart-visualization-skills](https://github.com/antvis/chart-visualization-skills).
Licensed under the [MIT License](https://github.com/antvis/chart-visualization-skills/blob/master/LICENSE).