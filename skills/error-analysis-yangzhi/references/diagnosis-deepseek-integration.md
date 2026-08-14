# DeepSeek 错因诊断API集成记录

## Prompt模板（CLTA_DIAGNOSE_PROMPT）

**铁律1：不能只说"概念不清"，必须指出具体哪个概念。**

```
你是初中数学诊断专家（基于CLTA学教评一致性框架、课标对齐和错因5分类法）。

**诊断要求：必须写出完整的因果关系，不能只贴标签。**

1. 错因类型 → 必须写出具体是哪个概念/哪条定理/哪个公式没理解
   - 概念不清：必须写出"不理解XX定理中XX的概念"
   - 方法不会选：必须写出"面对XX条件时不知用XX方法"
   - 步骤不完整：必须写出"漏了XX步，这一步为什么不能跳"
   - 审题不仔细：必须写出"漏了XX条件/看错了XX"
2. 判断依据：引用学生原话
3. 正确理解：用通俗语言解释
4. 追问引导：设计1-2个引导性问题（如"二次根式的被开方数有什么要求？"）
5. 变式练习：1道同类不同情境的题
```

## 前端API调用解包（铁律2）

所有后端API返回格式为 `{code: 0, data: {...}, message: "ok"}`，前端必须先解包：

```javascript
fetch('/api/v2/diagnose/analyze', { ... })
  .then(r => r.json())
  .then(data => {
    var diag = data;
    if (data.code !== undefined && data.data !== undefined) {
      diag = data.data || {};  // ← 必须解包
    }
    currentDiagnosis = diag;
    showDiagnosis(diag);
  });
```

**这条BUG导致OCR识别结果为空 + 诊断不显示两个问题。** 凡是通过 `api_v2()` 包装的响应，前端必须解包。

## 前后端API路径对齐（铁律3）

模块化重构时容易发生前端调旧路径、后端开新路径的不匹配。必须逐条比对：

```bash
# 前端调用的所有路径
grep -oP "fetch\('/api/v2/[^']+'" static/app.js
# 后端注册的所有路径  
grep -oP "@router\.(get|post|put|delete)\\(\"/api/v2/[^\"]+\"" routers/*.py
```

本项目中匹配到的差异：
- 前端 `fetch('/api/v2/ocr')` → 后端 `POST /api/v2/ocr/recognize`（缺recognize）
- 前端 `fetch('/api/v2/diagnose')` → 后端 `POST /api/v2/diagnose/analyze`（缺analyze）
- 前端 `fetch('/api/v2/generate-practice')` → 后端 `POST /api/v2/practice/generate`（路径不同）

## 多文件管理附加模式

每份材料独立存储OCR+诊断结果，参见 `references/multi-file-management-pattern.md`
