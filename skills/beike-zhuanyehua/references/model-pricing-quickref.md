# OpenRouter vs DeepSeek 模型定价速查

## DeepSeek V4 Flash 定价对比

| 渠道 | Prompt ($/token) | Completion ($/token) | 说明 |
|:----|:-----------------|:---------------------|:-----|
| DeepSeek官方 | 约 $0.10/百万token | 约 $0.20/百万token | 当前配置，直连稳定 |
| OpenRouter | $0.0983/百万token | $0.1966/百万token | 加了服务费，稍贵 |

**结论：DeepSeek V4 Flash 不是免费模型**，但极便宜。1元人民币≈1400万token。

## OpenRouter 免费模型（25个）
- `meta-llama/llama-3.3-70b-instruct:free`
- `google/gemma-4-31b-it:free`
- `google/gemma-4-26b-a4b-it:free`
- `qwen/qwen3-coder:free`
- `nousresearch/hermes-3-llama-3.1-405b:free`
- `nvidia/nemotron-3-super-120b-a12b:free`
- 等25个完全免费模型

## 当前配置（不动）
```
provider: deepseek
model: deepseek-v4-flash
base_url: https://api.deepseek.com/v1
```
走DeepSeek官方API已经是性价比最高的方案，无需更改。
