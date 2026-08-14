# LLM Provider 配置（学霸基本法诊断引擎）

> 2026-07-09 新增 MiniMax 支持

## 当前支持的 Provider

| Provider | 配置方式 | 成本 | 模型 |
|:---------|:---------|:-----|:------|
| **DeepSeek**（默认） | 环境变量 `DEEPSEEK_API_KEY` | 按量付费 | deepseek-chat |
| **MiniMax**（备选） | 环境变量 `MINIMAX_API_KEY` | 50亿免费Token | MiniMax-M3 |
| **OpenAI兼容** | base_url + api_key | 按量付费 | 自定义 |

## 切换 Provider

### LLMClient 构造函数
```python
# DeepSeek（默认）
client = LLMClient(provider="deepseek")
# DeepSeek 从 env DEEPSEEK_API_KEY 读取密钥

# MiniMax
client = LLMClient(provider="minimax")
# MiniMax 优先从 env MINIMAX_API_KEY 读取，没有则回退到 DEEPSEEK_API_KEY
```

### 环境变量
```bash
# DeepSeek（已配）
DEEPSEEK_API_KEY=sk-0c82...

# MiniMax（可选，获取免费50亿Token）
MINIMAX_API_KEY=your-minimax-key-here

# 通用
OPENAI_API_KEY=...
```

## 思路来源

博文「白嫖 50 亿 Token MiniMax」：MiniMax 提供免费层，无需注册即可用。可作为学霸基本法诊断引擎的低成本备选，缓解 DeepSeek API 调用费用。

## 接入状态

- [x] LLMClient 支持 provider 参数切换
- [x] MiniMax base_url = https://api.minimax.io/v1
- [x] MiniMax 模型名 = MiniMax-M3
- [x] API key 从环境变量读取
- [ ] 实际注册获取 MiniMax 免费 Token（用户需操作）
- [ ] 混合路由（同请求先试 MiniMax，失败回退到 DeepSeek）
