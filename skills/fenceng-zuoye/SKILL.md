---
name: fenceng-zuoye
description: 课堂练习分层设计 — 基础题·提升题·挑战题三层法。围绕同一学习目标，设计三种不同功能的练习，配合AI提示词模板快速生成
version: 1.2
author: 邱数智方教育部 · 李智蒸馏
source: 博文《课堂练习分层设计：一张表解决基础题、提升题、挑战题》(杨枝甘露加点糖)
category: education
---

# 分层作业设计 Skill

## 核心理念

真正好的分层练习，不是简单题、中等题、难题的排列，而是围绕**同一个学习目标**，设计三种不同功能的练习：

| 层级 | 解决什么问题 | 题目特征 | 教师观察点 |
|:----|:-----------|:---------|:-----------|
| **基础题** | 会不会（保底） | 直接、标准、步骤清楚 | 学生能否独立完成基本过程 |
| **提升题** | 懂不懂（纠偏） | 有变式、有干扰、有易错点 | 学生是否能说明理由，避开常见错误 |
| **挑战题** | 会不会迁移 | 情境新、条件变、表达开放 | 学生是否能选择方法、解释思路 |

## 设计前的三个自问

1. 这节课学生最基本要会什么？ → 基础题
2. 学生最容易在哪一步出错？ → 提升题
3. 如果学生已经掌握了，还可以往哪里提升？ → 挑战题

## 分层设计表（通用模板）

| 层级 | 练习目标 | 题目设计思路 | 示例题目 | 教师观察点 | 学生可能出现的错误 | 追问建议 |
|:----|:---------|:------------|:---------|:-----------|:-----------------|:---------|
| 基础题 |  |  |  |  |  |  |
| 提升题 |  |  |  |  |  |  |
| 挑战题 |  |  |  |  |  |  |

## 程序化练习生成（LLM API集成模式）

### 适用场景
诊断分析完成后，自动调用LLM生成分层练习，无需人工构造提示词。

### v2.0 升级：薄弱知识点驱动生成（2026-07-13）

**核心逻辑：** 从诊断结果的 `per_question` 中提取错题的 `concept_name`（具体知识点名），去重后作为「薄弱知识点」传给LLM，使练习题精准围绕学生的真正薄弱环节生成。

#### 完整数据流
```
诊断API返回
    ↓
前端提取错题 errors[] + 薄弱知识点 weakPoints[]（concept_name去重）
    ↓
fetch POST → /api/v2/practice/generate 携带 weak_points 字段
    ↓
PracticeRequest 模型接收 weak_points: list
    ↓
generate_practice() 函数构建 "薄弱知识点（请重点训练）" 提示区块
    ↓
LLM 收到错题+薄弱点+原始作业三重上下文
    ↓
生成三道分层练习题，每题标注 knowledge_point 字段
```

#### 前端实现（app.js）
```javascript
// 提取薄弱知识点（concept_name去重）
var weakPoints = [];
if (currentDiagnosis.per_question) {
  for (var i = 0; i < currentDiagnosis.per_question.length; i++) {
    var q = currentDiagnosis.per_question[i];
    if (!q.correct && q.concept_name && weakPoints.indexOf(q.concept_name) === -1) {
      weakPoints.push(q.concept_name);
    }
  }
}
// 传给API
body: JSON.stringify({
  diagnosis: currentDiagnosis,
  errors: errors,
  weak_points: weakPoints,
})
```

#### 后端Prompt注入（agent_service.py）
```python
weak_context = ""
if weak_points and len(weak_points) > 0:
    weak_context = "\n\n## 薄弱知识点（请重点训练）\n学生的薄弱知识点如下：\n" \
                 + "\n".join([f"- {wp}" for wp in weak_points])
CLTA_PRACTICE_PROMPT.format(error_context=error_context + weak_context, ...)
user_content = f"...重点训练薄弱知识点。每个题目必须标注knowledge_point。"
```

### v2.1 升级：Prompt精简+超时保护+防裸JSON泄漏（2026-07-14）

#### 性能优化关键参数

| 参数 | 旧值 | 新值 | 效果 |
|------|------|------|------|
| Prompt长度 | ~800字（含CLTA框架+分层表+格式对齐+双重JSON规格） | **~400字**（5条简明要求+一行JSON示例） | 首token延迟降低约40% |
| temperature | 0.6 | **0.3** | 输出更稳定，减少重试 |
| max_tokens | 2000 | **2000**（1200不够，3题+解析会被截断） | |
| API超时 | 180s | **25s** | 用户体验可控 |
| 超时fallback链 | 无 | DeepSeek(25s) → GLM(30s) → Ollama(120s) → 返回错误 | 三层兜底 |

#### Prompt写法——精简原则

**❌ 不要这样（~800字，慢）：**
```
你是数学练习设计师（基于CLTA学教评一致性框架 + fenceng-zuoye分层作业设计）。
## 核心要求
根据学生原始作业的题目格式，生成**格式完全一致**的纠正性练习题...
```

**✅ 应该这样（~400字，快）：**
```
你是初中数学出题老师。根据学生错题，生成{count}道分层练习题（基础/提升/挑战各1道）。
要求：
1. 只输出JSON，格式见下
2. 题目用"1. ""2. "编号，选项用"A. ""B. "
3. 每道题必须有question、options、answer、explanation、knowledge_point
4. 关注薄弱知识点
{error_context}
输出JSON格式：
{{"questions":[{{"level":"基础","question":"..."}}]}}
```

#### JSON示例花括号转义

Python `.format()` 视 `{}` 为占位符。JSON示例须用 `{{` `}}`：
```python
CLTA_PRACTICE_PROMPT = """...{{"questions":[{{"level":"基础"}}]}}..."""
# 经.format()后 → {"questions":[{"level":"基础"}]}
```

#### JSON解析——避免懒惰匹配陷阱

**❌ 错误：** `[\s\S]*?` 匹配在第一个 `}` 就停，对嵌套JSON只抓取内层
**✅ 正确：** 用brace_depth花括号计数提取完整JSON
```python
code_block = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', content)
if code_block:
    inner = code_block.group(1).strip()
    brace_depth = 0
    json_start = -1
    for ci, ch in enumerate(inner):
        if ch == '{':
            if json_start == -1: json_start = ci
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and json_start != -1:
                json_text = inner[json_start:ci+1]
                parsed = json.loads(json_text)
                questions = parsed.get("questions", [])
                break
```

#### 保护性fallback——防裸JSON泄漏

当JSON解析失败时，必须检测并屏蔽任何JSON格式残余：
```python
if not questions:
    plain = content.strip()
    plain = re.sub(r'```(?:json)?\s*', '', plain)
    stripped = plain.strip()
    is_json_like = stripped.startswith('{') or '{"questions"' in stripped
    if is_json_like or len(stripped) < 15:
        plain = f"请完成{topic}的分层练习题"
```

#### 前端硬超时保护（20s）

```javascript
var hardTimer = setTimeout(function() {
  pp.innerHTML = '<div class="rtab-empty">⏰ 生成超时（20秒），请重试</div>';
}, 20000);
// .then 和 .catch 都要 clearTimeout(hardTimer)
```

#### 常见陷阱

- ⚠️ **分析文本中的`{`干扰JSON提取**：不要直接从第一个`{`开始提取，优先找```json代码块；找不到时从最后一个`}`往回找对应`{`
- ⚠️ **GLM fallback调错函数**：`glm_client.diagnose(text)` 和 `glm_client.generate_practice(...)` 是两个不同方法。写fallback时务必检查调用是否正确
- ⚠️ **max_tokens过小致JSON截断**：3道题+options+explanation需约1500-2000 tokens。设1200会被截断

### 核心流程
```
前端触发(点击"理解继续") → 提取错题信息 → 构建结构化Prompt → 调用LLM API → 解析多格式JSON响应 → 渲染分层练习
```

### 关键实现模式（前端JavaScript）

#### 1. 错题数据提取
```javascript
// 从诊断结果中提取错题
var errors = [];
if (currentDiagnosis.per_question) {
  for (var i = 0; i < currentDiagnosis.per_question.length; i++) {
    var q = currentDiagnosis.per_question[i];
    if (!q.correct) {
      errors.push({number: q.number, error_analysis: q.error_analysis, error_type: q.error_type});
    }
  }
}
// 兜底：用整段分析文本
if (!errors.length && currentDiagnosis.analysis) {
  errors.push({number: 1, error_analysis: currentDiagnosis.analysis, error_type: '概念不清'});
}
```

#### 2. 主题提取（三优先级）
```javascript
var topic = '数学';
if (currentDiagnosis.error_types && currentDiagnosis.error_types.length > 0) {
  topic = currentDiagnosis.error_types.slice(0, 2).join(', ');  // ① 错因类型
} else if (currentDiagnosis.analysis) {
  var lines = currentDiagnosis.analysis.split('\n').filter(function(l) { return l.trim().length > 3; });
  topic = lines.length > 0 ? lines[0].substring(0, 60) : '数学';  // ② 分析首段
}
```

#### 3. 构建Prompt & API调用
```javascript
var errorContext = '## 学生错题数据\n以下是本次作业中的错题：\n';
for (var e = 0; e < errors.length; e++) {
  errorContext += '- 第' + errors[e].number + '题：错因=' + errors[e].error_type + '，分析=' + errors[e].error_analysis + '\n';
}
var practicePrompt = '请针对主题"' + topic + '"和以下错题生成3道分层练习题（基础/提升/挑战各1道），只输出JSON格式，不要其他文字。错题：\n' + errorContext;

fetch('/api/v2/diagnose/analyze', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({text: practicePrompt, session_id: sessionId, user_id: 'practice_gen'})
})
.then(function(r) { return r.json(); })
.then(function(data) { /* 解析JSON→渲染 */ });
```

#### 4. 多格式JSON解析（DeepSeek三大格式）
DeepSeek可能返回三种不同的JSON结构，前端必须能处理所有三种：

| 格式 | 示例 | 优先级 |
|------|------|--------|
| `{"questions": [...]}` | `{"questions": [{"level":"基础","question":"...","options":["A.","B."],"answer":"...","explanation":"..."}]}` | 最高 |
| `{"基础": {...}}` | `{"基础": {"题目":"...","答案":"...","解析":"..."}}` | 次高 |
| `{"exercises": [...]}` | `{"exercises": [{"level":"基础","question":"...","answer":"...","explanation":"..."}]}` | 第三 |

**解析实现**（按优先级检查）：
```javascript
var analysisText = data.data && data.data.analysis ? data.data.analysis : '';
var questions = [];

// 格式1: 直接找```json代码块
var jsonMatch = analysisText.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
if (jsonMatch) { questions = JSON.parse(jsonMatch[1]).questions || []; }

// 格式2: 找"questions"关键字上下文
if (!questions.length) {
  var qIdx = analysisText.indexOf('"questions"');
  if (qIdx < 0) qIdx = analysisText.indexOf('questions');
  if (qIdx >= 0) {
    var pre = analysisText.substring(0, qIdx);
    var startBrace = pre.lastIndexOf('{');
    if (startBrace >= 0) {
      /* 括号匹配提取 */
      var jsonStr = analysisText.substring(startBrace);
      var depth = 0, endPos = -1;
      for (var ci = 0; ci < jsonStr.length; ci++) {
        if (jsonStr[ci] === '{') depth++;
        else if (jsonStr[ci] === '}') { depth--; if (depth === 0) { endPos = ci + 1; break; } }
      }
      if (endPos > 0) {
        var parsed = JSON.parse(jsonStr.substring(0, endPos));
        questions = parsed.questions || [];
      }
    }
  }
}

// 格式3: 键值对 {"基础":{...},"提升":{...},"挑战":{...}}
if (!questions.length) {
  var parsed2 = JSON.parse(analysisText.trim());
  var converted = [];
  for (var lk in parsed2) {
    if (typeof parsed2[lk] === 'object' && parsed2[lk].题目) {
      converted.push({level: lk, question: parsed2[lk].题目 || '', options: parsed2[lk].选项 || [], answer: parsed2[lk].答案 || '', explanation: parsed2[lk].解析 || ''});
    }
  }
  questions = converted;
}

// 格式4: {"exercises": [...]}
if (!questions.length && parsed2 && parsed2.exercises) {
  questions = parsed2.exercises.map(function(e) { return {level: e.level || '练习', question: e.question || '', options: e.options || [], answer: e.answer || ''}; });
}
```

### 渲染输出
```javascript
function renderPractice(questions) {
  var phtml = '<div>📝 针对性练习（共' + questions.length + '题）</div>';
  for (var p = 0; p < questions.length; p++) {
    var q = questions[p];
    phtml += '<div class="practice-question">';
    phtml += '<div>第 ' + (p+1) + ' 题 · ' + (q.level || '巩固练习') + '</div>';
    phtml += '<div>' + (q.question || '') + '</div>';
    if (q.options && q.options.length > 0) {
      for (var o = 0; o < q.options.length; o++) {
        phtml += '<div class="practice-option">' + String.fromCharCode(65 + o) + '. ' + q.options[o] + '</div>';
      }
    }
    phtml += '</div>';
  }
}
```

### 陷阱
- ⚠️ **诊断API复用陷阱**：当专用练习路由损坏时，可复用诊断API（同一DeepSeek模型），只需换Prompt。但诊断API有系统prompt会包装响应——如果响应被诊断框架包裹，用"questions"关键字定位JSON
- ⚠️ **DeepSeek不保证JSON格式**：prompt要求"只输出JSON"时，DeepSeek可能仍会添加诊断包装文本。必须用多策略提取
- ⚠️ **level字段缺失**：DeepSeek有时不返回level字段，渲染时用`q.level || '巩固练习'`兜底
- ⚠️ **options缺失**：DeepSeek有时返回开放式题目（无选项），渲染时必须检查`q.options && q.options.length > 0`
- ⚠️ **服务器热重载双代码库**：修改后端代码后需完整重启（kill+start），热重载可能加载旧Python模块缓存。修改app.js等静态文件时无需重启

## AI提示词模板

给AI的提示词，不要只说"帮我出题"，要用结构化提示词：

```
我是一名【学段+学科】老师，正在设计一节课的课堂练习。

本节课主题是：【填写课题】。
本节课核心学习目标是：【填写目标】。
学生容易出现的问题是：【填写易错点或学情】。

请你不要直接堆题，而是帮我设计一张"分层课堂练习表"。
要求分为三层：
1. 基础题：用于检测学生是否掌握基本概念和基本方法；
2. 提升题：用于暴露易错点、混淆点和关键思维过程；
3. 挑战题：用于迁移运用或开放表达。

请用表格输出，每一层包括：
练习目标、题目设计思路、示例题目、教师观察点、学生可能出现的错误、追问建议。
```

## CLTA融合指引

在**备课专业化——学教评一致性**框架下，分层作业设计的落地要点：

| CLTA环节 | 分层作业对应 |
|:---------|:------------|
| 学习目标 | 三层练习围绕**同一个目标**，功能不同但不偏离 |
| 学情分析 | 基础题确认学情、提升题暴露盲区 |
| 教学活动 | 不同层次学生可同步进行不同难度的练习 |
| 评价任务 | 每层练习本身即为评价任务，观察学生能否通过 |
| 一致性检验 | 检验三层练习是否都指向同一学习目标 |

## 反例 vs 正例

| ❌ 反例（简单堆题） | ✅ 正例（有意图的分层） |
|:-------------------|:----------------------|
| 给全班同一套题 | 三层可选，学生按能力完成对应层级 |
| 基础题=简单题，挑战题=难题 | 基础题确保保底，挑战题测试迁移能力 |
| 只关注答案对错 | 关注学生能否说清思路和理由 |
| 题海战术，数量多 | 每层精选2-3题，质量优先 |

## 校本作业修订工作流（v1.1 新增）

当需要对已有校本作业/教辅进行分层修订时，使用以下工作流。

### 修订依据（四源评估法）

修订前必须同时对照以下四个依据：

| 依据 | 检查维度 | 来源 |
|:-----|:---------|:-----|
| ① 课程标准 | 知识点覆盖、核心素养要求 | 《义务教育数学课程标准（2022版）》 |
| ② 教材/教师用书 | 章节定位、教学建议 | 人教版对应年级教师用书 |
| ③ CLTA理念 | 学教评一致性 | 《备课专业化》框架 |
| ④ 分层作业框架 | 三层定位是否准确 | 本skill |

### 修订检查要点

| 检查项 | 常见问题 | 修改方向 |
|:-------|:---------|:---------|
| **学习目标** | 缺少目标陈述 | 每节开头加🎯学习目标（暂不入校本作业时可跳过） |
| **课前测** | 考新知识而非诊断已有知识 | 改为考查与本课相关的已有知识、前概念 |
| **课中测** | 题量偏多，与课后测区分不清 | 精减至2-3题，聚焦即时反馈和暴露问题 |
| **课后测·基础题** | 保底功能不清晰 | 保留核心题型，确保走通基本方法（2-3题） |
| **课后测·提高题** | 缺易错辨析设计 | 增加干扰项、变式题、典型错误辨析 |
| **课后测·挑战题** | 偏难题而非迁移题 | 改为联系实际情境 |
| **核心素养** | 纯数学题，缺"三会" | 增加生活应用题 |
| **自我评价** | 无自评环节 | 课后增加📊自评量规 |
| **答案** | 仅给结果 | 提高/挑战题增加💡解析和⚠️易错点 |

### 修订输出规范

```
E:\资料路径\
├── 校本作业（修订）\
│   ├── 第X章_题目_校本作业（修订）.docx
│   ├── 第X章_题目_答案（修订）.docx
│   ├── 第X章_题目_校本作业（修订）.md
│   └── images\
└── 修改意见\
    └── 第X章题目_修改意见.md
```

### 陷阱

- ⚠️ 修订不等于重编 — 保持原作业的整体结构和题量
- ⚠️ docx插图保留 — 几何作业的插图需从原docx提取后重新插入
- ⚠️ 答案同步修订 — 提高题/挑战题答案必须增加💡解析和⚠️易错点
- ⚠️ 课前测诊断已有知识 — 非预习新知识
- ⚠️ 功能层次 ≠ 难度层次 — 基础题保底，挑战题迁移，不是简单到难的线性排列
