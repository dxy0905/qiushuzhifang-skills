# 错因5分类法 · DeepSeek API集成记录

> 2026-07-06 · 学霸基本法V3

## 集成路径

错因5分类法（概念不清/方法不会选/步骤不完整/审题不仔细/迁移不足）已集成到学霸基本法的DeepSeek诊断Prompt中。

位于：`server/services/agent_service.py` → `CLTA_DIAGNOSE_PROMPT`

## Prompt模板 v3（生产级）

```python
CLTA_DIAGNOSE_PROMPT = """你是初中数学诊断专家（基于CLTA学教评一致性框架、课标对齐和错因5分类法）。
分析以下学生的答题内容。

**诊断要求：必须写出完整的因果关系，不能只贴标签。**

按以下格式逐项输出：

1. 错因类型（从以下5类中选最符合的一类）：
   - 概念不清 → **必须写出：具体是哪个概念/哪条定理/哪个公式没理解 + 正确理解**
   - 方法不会选 → **必须写出：面对什么条件时不知道该用什么方法 + 应该用什么方法**
   - 步骤不完整 → **必须写出：具体漏了哪一步 + 完整步骤是什么**
   - 审题不仔细 → **必须写出：具体漏了什么条件**
   - 迁移不足 → **必须写出：新旧情境的差异点**

2. 判断依据：引用学生原话。

3. 正确理解：用通俗语言解释。

4. 追问引导：设计1-2个引导性问题。

5. 变式练习：设计1道同类不同情境的题目。

学生回答：
{text}"""
```

## 后端提取逻辑

```python
def _extract_error_types(analysis: str) -> list[str]:
    types = ["概念不清", "方法不会选", "步骤不完整", "审题不仔细", "迁移不足",
             "概念不清", "计算失误", "审题不清", "方法不当", "知识断层"]
    found = []
    for t in types:
        if t in analysis and t not in found:
            found.append(t)
    return found if found else []
```

## 前端响应解包

所有 fetch 回调必须解包 `api_v2` 格式:
```javascript
.then(function(data) {
  var r = data;
  if (data.code !== undefined && data.data !== undefined) r = data.data || {};
  // 用 r.analysis, r.error_types, r.suggestions
})
```

## 验证记录

2026-07-06 测试通过：
- 输入："二次根式√(x-3)有意义，x范围？学生答x≥0"
- 输出：概念不清 → 具体指出"混淆了'x≥0'和'x-3≥0'" + 追问"二次根式的被开方数有什么要求？" + 变式"√(2x+4)有意义求x范围"
