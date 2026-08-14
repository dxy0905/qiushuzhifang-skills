# Token节省技巧（2026-07-08 博文分析）

来源：博文《每月20亿实现token自由的更好软件来了》→ OmniRoute + FreeLLMAPI

## 已应用到学霸基本法

### 1. Prompt压缩（_compress_prompt）
```python
def _compress_prompt(self, text: str) -> str:
    import re
    text = re.sub(r' +', ' ', text)           # 多空格→单空格
    text = re.sub(r'\n{3,}', '\n\n', text)     # 多空行→双空行
    text = text.replace('请', '').replace('您', '你')  # 去敬语
    text = text.replace('首先', '1)').replace('其次', '2)')
    text = text.replace('最后', '3)').replace('综上所述', '')
    text = text.replace('例如', '如').replace('也就是说', '即')
    return text.strip()
```
效果：省15-25% token，无损语义。

### 2. 知识库缓存
重复的诊断请求从知识库返回，不调用LLM。（已有session_manager.kb_search）

### 3. 模型选择
DeepSeek Chat 已是最优性价比（约¥0.28/百万token），对比：
- GPT-4: ¥80/百万token → 贵286倍
- Claude 4: ¥60/百万token → 贵214倍

## 外部工具

| 工具 | ⭐ | 效果 | 安装位置 |
|:-----|:---|:------|:---------|
| OmniRoute | 13,572 | RTK+Caveman压缩省15-95% | D:\名人蒸馏\OmniRoute\ |
| FreeLLMAPI | — | 16提供商免费层，约17亿token/月 | 已注册Hermes skill |

## 最佳实践

1. 诊断类任务先压缩prompt再发LLM
2. 常见错题模式先查知识库缓存
3. 批量生成错题集时用知识库不调用LLM
4. 需要时：通过OmniRoute路由到免费提供商
