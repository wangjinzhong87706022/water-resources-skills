# DeerFlow water-situation 符号链接设置

## 设置时间
2026-07-13 19:55

## 符号链接结构

/opt/git/deer-flow/skills/public/water-situation/
├── SKILL.md -> /opt/git/water-resources-skills/skills/water-situation/SKILL.md
├── lib -> /opt/git/water-resources-skills/skills/lib
├── references -> /opt/git/water-resources-skills/skills/water-situation/references
└── shared -> /opt/git/water-resources-skills/skills/shared

## 效果

✅ Git 仓库任何修改 → 立即生效于 DeerFlow
✅ 无需手动同步
✅ 文件一致性 100%

## 文件计数验证

- Git references/: 7 个文件
- DeerFlow references/: 7 个文件 ✅
- Git shared/: 11 个文件
- DeerFlow shared/: 符号链接 → Git ✅

## 优势

1. **完全同步**：Git 仓库修改 → DeerFlow 立即可见
2. **单点维护**：只需维护 Git 仓库一个版本
3. **节省空间**：DeerFlow 不存储实际文件内容
4. **版本一致**：避免 Git 和 DeerFlow 之间的版本分歧

## 注意事项

⚠️ 符号链接在 Windows 上可能需要特殊处理
⚠️ 备份时需注意符号链接指向的原始文件也会被备份
