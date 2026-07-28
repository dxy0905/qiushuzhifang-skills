# 预习引导 · 学霸基本法集成实现

> 参考博文来源：公众号「五宝奶爸学AI笔记」三篇
> 生成时间：2026-07-24

## 触发条件
学生开始学习新知识点（BKT概率<0.3且从未答过相关题目）

## 生成方式
1. 调 DeepSeek API + 教材skill（七上~九下数学.skill）生成预习单
2. 三步模板：找新概念→预测陷阱→思维路障
3. 分层标注：[必做]、[选做①]、[选做②]

## 预习完成验证
学生预习完后自动问两句话：
1. "这节课讲什么？" — 概括能力
2. "有什么问题要问？" — 提问能力

## 零预习兜底
学生没做预习时，10分钟课堂版：
1. 2分钟：翻到课本找3个关键词圈出来
2. 3分钟：两人一组互助分享
3. 5分钟：现场出一道简易预测题→切入正课

## 相关API
- `POST /api/v2/knowledge/identify` — 前置思考引导
- `GET /api/v2/knowledge/viz?student_id=xxx` — 知识图谱可视化（含预习起点判断）
- 预习生成：调 DeepSeek + `预习.skill` 中的提示词模板

## 部署位置
- 预习.skill：`/opt/xueba/server/skills/预习.skill/`
- AI教师Prompt：`/opt/xueba/server/prompts.py` / `PREVIEW_GUIDE_PROMPT`
