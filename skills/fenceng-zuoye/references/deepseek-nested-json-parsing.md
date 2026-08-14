# DeepSeek JSON解析实战：嵌套JSON + 超时fallback

## 问题描述

DeepSeek-v4-flash 生成分层练习题时，JSON解析总是失败：
- 返回的JSON有 ````json\n{...}\n```` 代码块包裹
- JSON含多层嵌套（3道题各有options数组）
- 懒惰匹配 `[\s\S]*?` 在第一个 `}` 就停止，只抓取内层对象

## 根因分析

```python
# ❌ 错误：懒惰匹配从{到第一个}就停
re.search(r'```(?:json)?\s*\n?(\{[\s\S]*?\})\s*\n?```', content)
# 输入: {"questions":[{"level":"基础",...}]}
# 捕获: {"level":"基础"}  ← 只抓了内层
```

## 正确做法：brace_depth花括号计数

```python
code_block = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', content, re.IGNORECASE)
if code_block:
    inner = code_block.group(1).strip()
    brace_depth = 0
    json_start = -1
    for ci, ch in enumerate(inner):
        if ch == '{':
            if json_start == -1:
                json_start = ci
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and json_start != -1:
                json_text = inner[json_start:ci+1]
                parsed = json.loads(json_text)
                questions = parsed.get("questions", [])
                break
```

## 策略2：无代码块时找完整JSON

```python
json_match = re.search(r'\{[\s\S]*\}', cleaned, re.DOTALL)
if json_match:
    json_text = json_match.group(0)
    # 必须验证闭合，防止截断JSON导致解析异常
    if json_text.count('{') == json_text.count('}'):
        parsed = json.loads(json_text)
```

## 保护性fallback：防止截断JSON泄漏

```python
plain = content.strip()
plain = re.sub(r'```(?:json)?\s*', '', plain)
plain = re.sub(r'\s*```', '', plain)
stripped = plain.strip()
# 检测JSON格式残余
is_json_like = stripped.startswith('{') or stripped.startswith('[') or '{"questions"' in stripped
if is_json_like or 'questions' not in plain or len(stripped) < 15:
    plain = f"请完成{topic}的分层练习题"
```

## 性能优化对照

| 优化项 | 改前 | 改后 | 效果 |
|--------|------|------|------|
| Prompt长度 | ~800字 | ~400字 | 首token延迟降40% |
| temperature | 0.6 | 0.3 | 输出稳定，少重试 |
| API超时 | 180s | 25s | 用户体验可控 |
| 超时fallback | 无 | DS→GLM→Ollama→报错 | 三层兜底 |
| JSON解析 | 懒惰regex | brace_depth计数 | 支持任意嵌套 |

## DeepSeek不稳定响应时间记录

实测10-25s波动，25s超时可覆盖90%场景：
- 最快: 9.6s
- 最慢: 24.7s (触发fallback边界)
- 平均: ~14s
