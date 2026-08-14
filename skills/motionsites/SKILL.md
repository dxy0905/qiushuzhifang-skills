---
name: motionsites
description: MotionSites AI 网页设计提示词库（144条 Framer Motion+Tailwind 设计 prompts）。当需要美化学霸基本法/任何网页页面、设计落地页、hero/footer 区块时使用。
version: 1.0
---

# MotionSites（AI 网页设计技能库）

## 定位
MotionSites（motionsites.ai）是 AI 网页设计提示词库——144 条 React + Tailwind CSS v4 + Framer Motion (`motion/react`) + lucide-react 的设计 prompts（hero/footer/pricing/背景等区块），可直接用于生成高质量动效落地页。

## 安装位置（2026-08-14）
- CLI：`motionsites`（npm 全局，v0.1.0）
- 数据集：`C:\Users\HUAWEI\.motionsites\registry.json`（144 resources，本地 registry）
- 辅助：`motion-sites-builder`（npm 全局，含 SKILL.md / motion_design_system.md）

## 常用命令（必须带 --registry 本地路径，线上 404）
```bash
R='C:\Users\HUAWEI\.motionsites\registry.json'
motionsites list --registry "$R"              # 列出全部
motionsites search <关键词> --registry "$R"    # 搜索（如 hero/education/pricing）
motionsites show <slug> --registry "$R"       # 查看一条（含完整 prompt）
motionsites pull <slug> --target markdown --output <path> --registry "$R" --force  # 导出 markdown
motionsites pull <slug> --target raw --output <dir> --registry "$R" --force         # 导出多文件包
```

## 关键模型
- 所有 prompt 均为：React + Tailwind CSS v4 + `motion/react` + `lucide-react`
- prompt 字段在 `search_keywords`（free_prompts.json 原始字段）
- 本地数据集源头：`C:\Users\HUAWEI\AppData\Roaming\npm\node_modules\motion-sites-builder\dataset\free_prompts.json`

## 美化网页工作流
1. `motionsites search <主题>` 找合适设计（如 search education / search hero）
2. `motionsites show <slug>` 看完整 prompt
3. 按 prompt 用 React+Tailwind+Framer Motion 重写目标页面
4. **邱董 UI 铁律**：'只微调/美化'=仅 CSS 级调整禁结构改动；竖排副标题≥14px/800；适配电脑/平板/手机全场景

## 注意
- CLI 的 show/pull 已本地修复（difficulty/frameworks/tags 缺省保护）
- 线上 registry https://motionsites.ai/registry.json 已 404，必须用本地 registry
