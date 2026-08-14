# DeepSeek-V4 Flash 练习生成JSON格式变体

## 背景
调用 DeepSeek-V4 Flash 生成分层练习题时，同一个prompt可能返回三种不同JSON结构。前端必须同时支持三种格式。

## 格式变体

### 格式1: `{"questions": [...]}` (标准数组)
```json
{
  "questions": [
    {
      "level": "基础",
      "question": "下列二次根式中，属于最简二次根式的是（  ）",
      "options": ["A. √12", "B. √(1/2)", "C. √18", "D. √7"],
      "answer": "D",
      "explanation": "最简二次根式要求：被开方数不含分母、不含能开得尽的因数..."
    }
  ]
}
```
**触发条件**：prompt中对JSON结构描述精确时

### 格式2: `{"基础": {...}, "提升": {...}, "挑战": {...}}` (键值对)
```json
{
  "基础": {
    "题目": "判断下列二次根式是否为最简二次根式，并说明理由：√18",
    "答案": "不是，可化简为3√2",
    "解析": "最简二次根式需要满足两个条件..."
  },
  "提升": {
    "题目": "下列二次根式中，哪些是最简二次根式？√12, √(a²+1), √(4b), √(x/2)",
    "答案": "只有√(a²+1)",
    "解析": "因为被开方数不含分母、不含可开方的因式..."
  },
  "挑战": {
    "题目": "若√(m²-4m+4)是最简二次根式，求整数m的取值范围。",
    "答案": "m≠2",
    "解析": "当m=2时被开方数为0..."
  }
}
```
**触发条件**：prompt要求"基础/提升/挑战各1道"时，DeepSeek会用层级名作为键
**注意**：键名可能是中文"基础""中等""提高""挑战"，需统一映射

### 格式3: `{"exercises": [...]}` (替代数组)
```json
{
  "exercises": [
    {
      "level": "基础",
      "question": "下列二次根式中，哪些是最简二次根式？",
      "answer": "B和E",
      "explanation": "最简二次根式要求..."
    }
  ]
}
```
**触发条件**：prompt中包含"练习题"或"exercises"关键词时
**注意**：可能缺少`options`字段（开放式题目）

## 解析策略优先级

```
1. 查找```json或```代码块 → 提取完整JSON
2. 查找"questions"关键字 → 括号匹配提取
3. 直接JSON.parse → 检查是否为键值对格式（有"题目"字段）
4. 检查"exercises"关键字 → 括号匹配提取
5. 所有方法失败 → 显示"练习生成失败，请重试"
```

## 选项前缀去重

DeepSeek返回的`options`字段**可能已包含**字母前缀（`"A. √12"`, `"B. √(1/2)"`），但前端渲染时也会加前缀。若不处理会出现`A. A. √12`。

**前端修复**：渲染前清洗每个选项：
```javascript
var optText = q.options[o];
optText = optText.replace(/^[A-Za-z][.、．)\s]*/, '').trim();
// 然后用 String.fromCharCode(65 + o) + '. ' + optText 重新加前缀
```

## KaTeX竖排文字陷阱

诊断分析文本中若出现**孤立的`$`符号**（如`$2`、`完整步骤的叙述中混有$符号`），KaTeX的自动渲染会将`$`视为行内数学公式定界符，导致：
- `$2`被解析为数学公式"2"→渲染异常→字符粘连竖排显示
- 诊断分析容器中的文字被`$`打断，后续文本显示错位

**修复方案**（双重防护）：
```javascript
// ① KaTeX配置：throwOnError: false 遇到解析错误跳过不渲染
renderMathInElement(element, {
  delimiters: [
    {left: '$$', right: '$$', display: true},
    {left: '\\(', right: '\\)', display: false},
    {left: '$', right: '$', display: false}
  ],
  throwOnError: false  // 关键：防止$2等触发报错
});

// ② CSS防止字符竖排
contentDiv.style.cssText += ';word-break:normal;white-space:normal;overflow-wrap:break-word';
```

## 答案管理模式

练习生成后**不直接显示答案**，学生先做题，点击按钮后才弹出：

```html
<!-- 第三栏底部新增按钮 -->
<span class="ub" id="bAnswer" onclick="showPracticeAnswers()" style="background:#e67e22;color:#fff">练习<br>答案</span>
```

```javascript
function showPracticeAnswers() {
  var qs = currentDiagnosis.practice;
  var html = '<div>📋 练习答案</div>';
  for (var i = 0; i < qs.length; i++) {
    html += '<div>第' + (i+1) + '题 · ' + (qs[i].level || '') + '</div>';
    if (qs[i].answer) html += '<div>✅ 答案: ' + qs[i].answer + '</div>';
    if (qs[i].explanation) html += '<div>📖 解析: ' + qs[i].explanation + '</div>';
  }
  // 弹出遮罩模态框
  var overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center';
  overlay.onclick = function() { document.body.removeChild(overlay); };
  var box = document.createElement('div');
  box.style.cssText = 'background:#fff;border-radius:12px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto;padding:16px';
  box.innerHTML = html;
  overlay.appendChild(box);
  document.body.appendChild(overlay);
}
```

## 后端服务不可重启时的变通方案

当后端Python进程（如PID 5496）无法被杀死/重启时（taskkill /F失败、wmic找不到、Stop-Process报错），修改后端路由不会生效——Python模块缓存了旧代码。

**变通方案**：仅修改前端静态文件（app.js、index.html），让旧后端做它已能做的事（如诊断API `/api/v2/diagnose/analyze`），用新前端代码绕过后端瓶颈：

| 原计划 | 变通方案 |
|--------|---------|
| 新增/修改后端路由 | ❌ 不可行（代码不加载） |
| 修改app.js → 调用不同API端点 | ✅ 可行（静态文件每次请求都重新读取） |
| 修改index.html → 新增按钮 | ✅ 可行 |

## 验证方法
```python
# 快速测试当前API返回格式
import requests, json
r = requests.post('http://localhost:8000/api/v2/diagnose/analyze',
    json={'text': practice_prompt, 'session_id': 'test', 'user_id': 'practice_gen'},
    timeout=120)
text = r.json().get('data', {}).get('analysis', '')

# 检测格式
if '"questions"' in text: print("Format 1 (questions[])")
elif text.find('{') >= 0:
    parsed = json.loads(text[text.find('{'):])
    has_keys = [k for k in parsed.keys() if k in ('基础','提升','挑战','中等')]
    if has_keys: print(f"Format 2 (keys: {has_keys})")
    elif 'exercises' in parsed: print(f"Format 3 (exercises: {len(parsed['exercises'])} items)")
```
