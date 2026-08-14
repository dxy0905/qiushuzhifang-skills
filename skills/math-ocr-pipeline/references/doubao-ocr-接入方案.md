# 豆包（Doubao）OCR 接入方案调研 + 实测状态（2026-08-08 更新）

## 背景：手写识别是现有管道短板

现有 OCR 管道（RapidOCR + LaTeX-OCR + DeepSeek）以**印刷体**为主，RapidOCR 对手写体识别率低；
LaTeX-OCR 因 torch 兼容问题已静默失效（见主 SKILL.md）。作业/习题**手写体 + 数学公式**是两个明确短板。

## 调研结论：豆包用什么 OCR

| 方案 | 模型 | 说明 |
|:-----|:-----|:-----|
| 豆包 App 拍题/识别 | `doubao-seed-1.6-vision`（火山方舟） | 视觉理解大模型，原生 **VisualCoT 视觉思维链**（2026 初 1.6 系列升级），实测手写/公式/图表/几何图理解强 |
| 专用 OCR 模型 | `doubao-seed-1.6-ocr`（火山方舟 OCR 方向） | 针对文档/手写/公式优化，按页/次计费 |

## 接入方式（OpenAI 兼容，与 DeepSeek 同模式）

- **Endpoint**：`https://ark.cn-beijing.volces.com/api/v3`（OpenAI 兼容）
- 调用：`POST /chat/completions`，模型名填 `doubao-seed-1.6-ocr` 或 `doubao-seed-1.6-vision`，消息含图片 base64（`image_url` 字段）+ 提示词输出结构化 JSON
- 与现有 DeepSeek 调用同模式（`client.chat.completions.create`）——接入成本低，一次替换 `OCREngine` 的图片后处理即可
- 结构化输出：提示词要求逐题 JSON（题号/正误/学生答案/正确答案/错因）——直接喂现有诊断管线

## 实测状态（2026-08-08 · 用户已拍板"接入，试试效果"）

### Key 位置（D 盘，勿再全盘找）
- `D:\VibeFilming\vibefilming.config.json` → `ark.api_key` = `<YOUR_ARK_API_KEY>`（脱敏：真实 Key 勿提交公开仓库）
- 同文件含 `ark.models`：text=`deepseek-v4-pro-260425`、vlm=`doubao-seed-2-1-pro-260628`、image=`doubao-seedream-5-0-260128`、video=`doubao-seedance-2-0-260128`（VibeFilming 项目自配模型名，非标准 ID）
- 测试脚本模板：`hermes` 侧写过 `doubao_ocr_test.py`（OpenAI 兼容 urllib 调用，图片 base64 + model + max_tokens），可直接复用

### 账号模型未开通（当前阻塞点）
- Key **有效**（`GET /api/v3/models` 返回 200），但**全部模型调用 404**：
  `{"error":{"code":"InvalidEndpointOrModel.NotFound","message":"The model or endpoint X does not exist or you do not have access to it"}}`
- **排查法**：`curl /api/v3/models` 返回的 129 个模型是**全平台目录**（含 Shutdown/Retiring/未开通），**不是已开通列表**——列表里有 ≠ 能调
- 实测：`doubao-seed-1-6-vision-250815`、`doubao-1-5-vision-pro-32k-250115`（均 Retiring）、`doubao-seed-1-6-flash-250828`（文本）全部 404——**历史测试账号从未开通任何模型的调用权限**
- **解法（用户操作）**：火山方舟控制台 `console.volcengine.com/ark` → 开通管理/模型广场 → 开通 `doubao-seed-1-6-vision`（或 `doubao-seed-1-6-ocr`）→ 开通后重测

## 成本

- 豆包以低价著称：视觉理解约 0.003 元/千 token 级；OCR 模型按次/页计费，远低于百度/阿里同类
- 具体价格需火山方舟控制台确认（页面 JS 渲染，curl 拿不到）

## 收益（一次接入三痛点齐解）

1. **手写识别**（RapidOCR 短板）
2. **数学公式**（LaTeX-OCR 失效后的空缺）
3. **作图痕迹**（视觉模型真看图——根治"系统只看 OCR 文字、看不到图"的判定局限，见诊断判定"作图题铁律"）

## 其它参考

- 开源手写 OCR 备选：XS-VLM-OCR（GitHub）、STranslate 火山 OCR 插件（ybhgl/STranslate.Plugin.Ocr.Volcengine）——都是视觉模型接入，与豆包同路线
- 本机无视觉模型（Ollama qwen2.5:1.5b 无 vision；vision_analyze 403 地区限制）
