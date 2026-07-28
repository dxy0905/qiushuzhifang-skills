# 练习生成 Troubleshooting 笔记

## 已知问题

### 问题1：JSON包裹显示 `{ "questions": [...] }`

**现象：** 测试练习面板显示原始JSON `{ "questions": [ { "level": "基础", "question": "...", "options": [] } ] }`

**根因：** LLM返回的内容包含代码块标记(````json`)且JSON有嵌套，后端正则`[\s\S]*?`(非贪婪)只匹配到第一个`}`，导致解析失败，回退为纯文本插入。

**修复方案（2026-07-13）：**
- 后端：先用`.startswith('```')`检测并剥离代码块标记，再直接`json.loads()`；失败后用贪婪`\{.*\}`+`re.DOTALL`匹配
- 前端：`renderPractice()`加三层兜底：(1)`typeof q === 'string'`时解析 (2)`q.question`含JSON包裹时提取 (3)截断至200字符

**验证方法：**
```python
curl -s "http://127.0.0.1:8080/api/v2/practice/generate" \
  -H "Content-Type: application/json" \
  -d '{"diagnosis":{"per_question":[{"number":1,"correct":false,"concept_name":"数轴","error_type":"概念不清"}]},"count":3}'
# 预期：返回data.questions数组，每个元素有question字段

```

### 问题2：登录按钮读取错误字段

**现象：** 点击登录无响应，或使用注册页数据登录

**根因：** 登录按钮事件监听中读取了注册页的字段ID（`pwdPm`、`acctPm`、`smsCode`），而非登录页字段ID（`pwd`、`acct`、`code`）

**修复：** 将`localStorage.getItem('acctPm')`改为`document.getElementById('acct').value`，`#pwdPm`改为`#pwd`，`#smsCode`改为`#code`

### 问题3：诊断/练习耗时过长（10-109秒）

**现象：** 用户报告诊断或练习生成耗时数分钟，页面"卡死"

**根因：** DeepSeek API处理时间5-40秒，重试2次可长达120秒

**修复方案：**
- 诊断总耗时超过60秒自动跳转到GLM-4.7-Flash免费模型
- GLM也失败则跳转到Ollama本地模型
- 前端增加15秒超时提醒："正在生成，已超过15秒仍在努力"

## 诊断备用模型配置

```bash
# .env 配置
ZHIPU_API_KEY=9b5dd6be953c4fb789a78efeb7ef7461.qadsViRcMLbZGmmp
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4.7-flash

# DeepSeek（已有）
DEEPSEEK_API_KEY=sk-ba9...40aa
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

## 降级链

```
DeepSeek-V4-Flash（主）→ GLM-4.7-Flash（免费备用）→ Ollama qwen2.5:1.5b（本地）
```

## 注册验证码测试

测试阶段所有手机验证码可使用 `000000` 通过。在 `sms_service.py` 的 `verify_code()` 中实现。
