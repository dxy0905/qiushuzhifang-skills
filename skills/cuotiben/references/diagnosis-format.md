# 错因诊断格式规范

> 依据：邱董要求"注明哪一题，具体错在哪，给出详细说明"
> 更新日期：2026-07-09（v7两步诊断版 + 三级置信度）

## 两步诊断法

### 第一步：整体判断
先列出每题的对错清单：

```
- 第1题：✅ 正确（√3是最简二次根式）
- 第2题：❌ 错误（√20可化简为2√5）
- 第3题：❌ 错误（x≥5写成了x=-3）
```

### 第二步：逐题详细分析
每道题按以下8个字段输出：

```
【第X题】
1. 题号：第X题
2. 正误：✅ 做对了 / ❌ 做错了
3. 学生答案：学生写了什么
4. 正确答案：应该是什么
5. 具体错在哪：精确到哪个数字/符号/步骤
6. 错因类型：[概念不清|方法不会选|步骤不完整|审题不仔细|迁移不足]
   → 概念不清必须写具体概念名，不得用"概念不清"四字概括
   → 必须区分"二次根式的概念没掌握"还是"二次根式的运算没学会"
7. 详细说明：推理链条在哪里断了 / 这个错误的本质是什么
8. 正确理解、追问引导、变式练习
```

## Prompt核心规则

| 规则 | 说明 |
|:-----|:------|
| 先整体再逐题 | 先列每题对错，再逐题深入 |
| 必须写题号 | 每题以【第X题】开头 |
| 禁用"概念不清"四字 | 必须写具体知识点 |
| 区分概念vs运算 | 分清是概念问题还是运算问题 |
| DeepSeek输出含markdown加粗 | 前端已设 `white-space:pre-wrap` 不丢失格式 |

## 三级置信度标签（前端渲染）

| 置信度 | 分界值 | 标签 | 决策 |
|:------:|:------:|:----|:------|
| high | ≥50 | 🟢 高置信度 | 自动出诊断 |
| medium | 20-49 | 🟠 建议复核 | 暂停，标给教师 |
| low | <20 | 🔴 置信度低 | 提示重拍/人工 |

前端 `app.js` → `showDiagnosis()` 读取 `data-confidence` 字段，自动渲染对应颜色标签。

## 诊断API返回结构

```json
{
  "analysis": "【第1题】...",
  "error_types": ["概念不清"],
  "suggestions": ["回归课本理解最简二次根式定义"],
  "confidence": "high",
  "data-confidence": "high"
}
```

## 实现位置

| 组件 | 文件 | 行号/函数 |
|:-----|:-----|:----------|
| 提示词模板 | `server/services/agent_service.py` | `CLTA_DIAGNOSE_PROMPT_TEMPLATE` (~L328) |
| 置信度检查 | `server/services/agent_service.py` | `OCREngine._check_ocr_quality()` (~L782) |
| 诊断调用 | `server/services/agent_service.py` | `LLMClient.diagnose()` (~L416) |
| API路由 | `server/routers/agent_routes.py` | `/api/v2/diagnose/analyze` (~L597) |
| 前端渲染 | `server/static/app.js` | `showDiagnosis()` (~L686) |

## 常见陷阱

| 问题 | 修复 |
|:-----|:------|
| DeepSeek输出带markdown **加粗** | 前端文本容器已设 `white-space:pre-wrap` |
| 长篇诊断被截断 | `max_tokens=1000` 不够时可调到2000 |
| 置信度为high但诊断质量差 | 根因是OCR不准，不是置信度本身问题 |
| 诊断结果刷新后丢失 | 前端已实现IndexedDB持久化（saveRecord/loadRecords） |
