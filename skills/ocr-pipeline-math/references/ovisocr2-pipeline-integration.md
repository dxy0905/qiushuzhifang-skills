# OvisOCR2 集成（已实施 · 2026-08-02 · commit fdd85ec）

## 状态
✅ **已实施并部署**（本会话完成）：`server/services/ocr_pipeline.py` 三级降级链已上线，
实测通过，commit fdd85ec 已推送生产。Ollama 在开发机可用时走 OvisOCR2，
生产 ECS 无 Ollama 自动降级 MinerU（设计如此，不影响功能）。

## 三级降级链（已落地）

```
OvisOCR2（首选） → MinerU（回退） → RapidOCR（兜底）
```

`run_pipeline()` 第2步实现（2a/2b/2c 三段）：
- 2a: `ovisocr2_parse(file_path)` — 产出<20字符则降级
- 2b: `mineru_parse(file_path)` — 现有逻辑保留
- 2c: RapidOCR（OCREngine）兜底

## 无GPU部署配方（本机 Windows，无CUDA）

**模型来源**：阿里 ATH-MaaS/OvisOCR2（0.8B，Qwen3.5-0.8B 后训练，
OmniDocBench v1.6 96.58 分 SOTA，Apache-2.0）。官方推理需 vLLM+GPU；
**无 GPU 用 GGUF 量化版**：`Abiray/OvisOCR2-GGUF`（hf-mirror 下载，HF 被墙）。

```bash
# 1. 下载（hf-mirror.com 替代 huggingface.co——大陆网络必需）
mkdir -p ~/OvisOCR2 && cd ~/OvisOCR2
curl -sL -o OvisOCR2-Q5_K_M.gguf "https://hf-mirror.com/Abiray/OvisOCR2-GGUF/resolve/main/OvisOCR2-Q5_K_M.gguf"   # 551MB
curl -sL -o mmproj-F16.gguf "https://hf-mirror.com/Abiray/OvisOCR2-GGUF/resolve/main/mmproj-F16.gguf"          # 195MB 视觉投影器

# 2. Modelfile（多模态必须 ADAPTER 指向 mmproj！）
cat > Modelfile << 'EOF'
FROM ./OvisOCR2-Q5_K_M.gguf
ADAPTER ./mmproj-F16.gguf
TEMPLATE """<|im_start|>system
You are OvisOCR2, a document parsing model. Convert document page images into clean Markdown. Format formulas as LaTeX, tables as HTML.<|im_end|>
<|im_start|>user
{{.Prompt}}<|im_end|>
<|im_start|>assistant
"""
PARAMETER temperature 0.0
PARAMETER num_predict 4096
EOF

# 3. 创建 + 验证
ollama create ovisocr2 -f Modelfile
ollama list | grep ovis   # → ovisocr2:latest 782MB
```

**量化选型**：Q5_K_M 578MB（低资源推荐）；精度优先用 Q8_0 812MB 或 BF16 1.52GB。
Q5 对极复杂表格有损，升级 Q8_0 可改善。

## 调用（Python，base64 图片 → Ollama API）

```python
import base64, json, urllib.request
with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
payload = {
    "model": "ovisocr2",
    "prompt": "Extract all readable content from the image in natural human reading order "
              "and output the result as a single Markdown document. "
              "Format formulas as LaTeX. Format tables as HTML: <table>...</table>. "
              "Preserve the original text without translation or paraphrasing.",
    "images": [b64], "stream": False,
    "options": {"temperature": 0.0, "num_predict": 4096},
}
req = urllib.request.Request("http://127.0.0.1:11434/api/generate",
    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=180)
text = json.loads(resp.read())["response"]
if "</think>" in text:          # 清理思维链标记（Qwen系会输出）
    text = text.split("</think>")[-1].strip()
```

## 实测数据（2026-08-02）

- 中文数学试卷图（标题/选择题/解答题/公式）→ 3.2秒解析成功
- 输出：Markdown 结构化（## 标题）+ 公式转 LaTeX（`$x+5=12$`）+ 中文识别
- split_into_problems 拆出 2 道题（合理）
- 对比 MinerU：3秒 vs 180秒超时（60倍提速）
- 日志确认：`✅ OvisOCR2解析成功（101字符）`，无降级日志

## 陷阱

1. **中文测试图渲染**：PIL 默认字体不支持中文 → 测试图标题乱码/变[1]。
   必须加载系统字体 `C:\Windows\Fonts\msyh.ttc`（微软雅黑）再生成测试图。
2. **mmproj 缺失**：Ollama Modelfile 不加 `ADAPTER` 会报多模态不可用——GGUF 多模态模型
   = 主模型 + 视觉投影器两个文件，两者都要下。
3. **Qwen3.5 输出带 `<think>`**：需 split("</think>") 清理（已内置）。
4. **生产 ECS 无 Ollama**：`_ollama_available()` 检测失败自动跳过 OvisOCR2 → 降级链正常。
5. **`</think>` 位置**：有的输出在开头，split 取最后一段即可。

## 代码位置（当前实现）

- `server/services/ocr_pipeline.py`：
  - `_ollama_available()` — Ollama 服务+模型检测
  - `ovisocr2_parse_image()` — 单图 → Markdown
  - `ovisocr2_parse()` — 入口（图片直接/PDF逐页 pdftoppm）
  - `run_pipeline()` 2a/2b/2c — 三级降级链
- 端点不变：`POST /api/v2/ocr/enhanced`
- 配置文档：`D:\邱数智方\技术局\OvisOCR2配置说明.md`
