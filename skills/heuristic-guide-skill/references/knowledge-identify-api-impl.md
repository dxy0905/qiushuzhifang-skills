# 前置思考引导 API 实现（2026-07-24 部署）

## 功能
在学生提交题目后、正式诊断前，AI先问"这道题考的是哪部分知识？"引导学生主动思考知识归类。

## 后端改动

### 1. prompts.py — 新增KNOWLEDGE_IDENTIFY_PROMPT
包含50条引导语模板，AI随机选取一句输出。

### 2. agent_service.py — LLMClient 新增方法
```python
def knowledge_identify(self, text: str) -> dict:
    """前置思考引导"""
    guiding_question = ""
    try:
        import os
        from openai import OpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if api_key:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": KNOWLEDGE_IDENTIFY_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.5,
                max_tokens=200,
            )
            guiding_question = resp.choices[0].message.content.strip()
    except Exception:
        guiding_question = ""
    knowledge_matches = search_knowledge(text[:80])
    return {
        "guiding_question": guiding_question,
        "knowledge": [{"name": k["name"], "desc": k.get("desc", "")} for k in knowledge_matches[:3]],
    }
```

### 3. agent_routes.py — 新增API路由
```
POST /api/v2/knowledge/identify
Body: {"text": "题目内容"}
Response: {"code": 0, "guiding_question": "先别急着算...", "knowledge": [...]}
```

### 注意事项
- API key 通过环境变量 `DEEPSEEK_API_KEY` 获取，不从config import
- `search_knowledge` 子串匹配有时匹配不到（如"直角"→"勾股定理"不匹配），可改用ChromaDB向量检索
- 前端在诊断面板加载前调此接口，显示引导框，学生点击"我想好了"后再展示诊断结果

## 部署服务器
学霸基本法 ECS: 8.145.57.233
服务目录: /opt/xueba/server/
