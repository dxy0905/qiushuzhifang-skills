---
name: ocr-pipeline-math
description: |
  数学作业OCR增强管道——面向初中数学作业/试卷图片的智能识别流水线。
  组合MinerU(版面分析) + RapidOCR(通用文字) + LaTeX-OCR(公式识别) + DeepSeek(错因诊断)。
  最终输出逐题错因分析 + 整份作业综合评价。
---

# OCR增强管道 · 数学作业智能识别

## OvisOCR2 三级降级链（2026-08-02 已实施 · commit fdd85ec）

```
OvisOCR2（首选·0.8B端到端·3秒） → MinerU（回退·180秒） → RapidOCR（兜底）
```

`run_pipeline()` 第2步：先 `ovisocr2_parse()`，产出<20字符降级 `mineru_parse()`，
再不足降级 RapidOCR。OvisOCR2 用 Ollama 跑 GGUF（无GPU也可），开发机可用时走它，
生产 ECS 无 Ollama 自动降级（设计如此）。中文公式转 LaTeX、表格转 HTML，
实测 3.2秒 vs MinerU 180秒（60倍提速）。完整部署配方+陷阱见
`references/ovisocr2-pipeline-integration.md`。

### OvisOCR2 兼作本地图像理解引擎（2026-08-02 实战）

当 browser_vision / vision_analyze 不可用（403 区域限制）时，OvisOCR2 可当本地视觉理解引擎用——
传 `images:[base64]` + 自然语言问题，返回文本描述（结构化列表/布局/配色等）：

```python
import base64, json, urllib.request
with open(img_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
payload = json.dumps({'model': 'ovisocr2', 'prompt': '描述此页面布局：1.顶部导航 2.分区内容...', 'images': [b64], 'stream': False}).encode()
req = urllib.request.Request('http://127.0.0.1:11434/api/generate', data=payload, headers={'Content-Type': 'application/json'})
resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
print(resp.get('response', ''))
```

**能力边界（Q5_K_M 量化版实测）：**
- ✅ 识别页面结构/标题/导航Tab/主色调（"学习中心/学习主页/错因分析/AI老师/我的目标/蓝"）
- ✅ 中英文文本、公式
- ⚠️ 输出偏简短（量化精度限制）——复杂布局细节不全，需针对性引导prompt
- ⚠️ 相比专用视觉模型（GPT-4V等）描述粒度粗——适合"确认布局骨架"，不适合"像素级美学评估"
- 升级 Q8_0（812MB）可提升精度；要精细视觉分析仍优先专用模型

## MinerU V2 集成（2026-07-18）- 同时支持图片+PDF

重写后的 `ocr_pipeline.py` 使用 MinerU CLI 作为统一入口，自动识别文件类型：

### 文件类型路由
| 类型 | MinerU 参数 | 说明 |
|:----|:------------|:------|
| `.pdf` | `--method auto --backend pipeline` | PDF 走自动识别，pipeline 后端（CPU 兼容） |
| `.jpg/.png/...` | `--method ocr --backend pipeline` | 图片走 OCR 模式 |
| 其他 | 拒绝 (400) | 只允许 `.pdf/.jpg/.jpeg/.png/.bmp/.tiff/.webp` |

### 回退机制
MinerU 产出不足（full_text < 20 字符）时自动回退 RapidOCR。

### API 端点
`POST /api/v2/ocr/enhanced` 接受 multipart/form-data 的 file 字段，支持 PDF/图片。
响应包含 `file_type: "pdf" | "image"` 字段。

### MinerU 版本
- `mineru 3.4.0`（pip 安装）
- CLI：`mineru -p <path> -o <output_dir> --method <auto|ocr|txt> --backend <pipeline|hybrid-engine> -l ch`
- 180 秒超时
- 输出文件：`.md` / `.json` / `.txt`

## 架构

```
图片上传 → 降采样 → MinerU版面拆题 → RapidOCR+LaTeX-OCR识别
→ 数学符号修正 → DeepSeek错因诊断 → 综合评估
```

## 组件

| 组件 | 安装 | 权重 |
|:-----|:------|:------|
| OvisOCR2 | GGUF+Ollama（见references/ovisocr2-pipeline-integration.md） | 782MB（Q5_K_M） |
| MinerU | pip install mineru | 2.2GB（modelscope.cn） |
| LaTeX-OCR | pip install pix2tex | 97MB（GitHub Release） |
| RapidOCR | pip install rapidocr-onnxruntime | 无（模型内嵌） |

## 关键文件

- 管道代码: `server/services/ocr_pipeline.py`
- API路由: `POST /api/v2/ocr/enhanced`
- 数学符号修正: `OCREngine._fix_math_symbols()`
- CLTA诊断: `CLTA_DIAGNOSE_PROMPT_TEMPLATE`

## 数学符号纠错（三层架构）

`OCREngine._fix_math_symbols()` 使用三层修复架构。完整版（含全角转半角/希腊字母/百分号/约等号/中点乘号/括号平衡等+50行）见 `company-skills/math-ocr-pipeline`。以下为关键模式摘要：

### 第1层：基本替换
| 模式 | 替换 | 说明 |
|:-----|:------|:------|
| `V`/`J`/`>Q.X7`/`VX`/`JX` | `√` | 根号 |
| `士` | `±` | 正负号 |
| `!=`/`! =` | `≠` | 不等号 |
| `<=`/`< =` | `≤` | 小于等于 |
| `>=`/`> =` | `≥` | 大于等于 |
| `~~`/`~=` | `≈` | 约等于（新增） |
| `兀`/`TT` | `π` | 圆周率（新增） |
| `△` | `Δ` | 增量（新增） |
| `0/0`/`°/°`/`0/o` | `%` | 百分号（新增） |

### 第2层：全角转半角
全角数字/字母/运算符→半角，包括：`０-９`→`0-9`, `Ａ-Ｚａ-ｚ`→`A-Za-z`, `＋－×÷＝＜＞（）．，：`→`+-×÷=<>().,:`

### 第3层：上下文正则修复（关键模式）

| 模式 | 原始OCR | 修正后 | 说明 |
|:-----|:---------|:-------|:-----|
| 变量x→数字1 | `1≤3` | `x≤3` | 后顾断言保护多位数 |
| 根号括号 | `√x+4` | `√(x+4)` | 表达式补全，含末端缺括号 |
| 上标 | `x^2`/`x2`/`x^3`/`x3` | `x²`/`x³` | 支持2/3/⁻¹ |
| 大写X | `X≥0` | `x≥0` | 数学上下文中 |
| 中点乘号 | `3·5` | `3×5` | ⚠️不在第1层直接删· |
| 分数横线 | `---`/`___` | `─` | 连续3+横线→分数线 |
| 选项空格 | `A.√7` | `A. √7` | 选项后补空格 |
| 括号平衡 | `√(x+4(` | `√(x+4())` | 补末尾缺失括号 |
| 数字中点 | `0. 01` | `0.01` | 小数点多空格 |
| 取值范围 | `取值范围是1≤3` | `取值范围是x≤3` | 特定语境1→x |

### ⚠️ 修复顺序陷阱
1. 基本替换→全角转半角→正则修复（**顺序不可颠倒**）
2. 不要在基本替换中用`("·","")`无脑删除中点（破坏第3层中点乘号匹配）
3. "进步1）"修复放在全角转半角之后（因为`）→)`）
4. 全角转半角在正则之前，否则第3层正则匹配不到全角符号

### 8开试卷降采样 + 图像预处理

大尺寸试卷图片（8开/A3扫描件，常见3500×2500px以上）会导致OCR超时或OOM。**降采样+图像增强**一起做：

```python
from PIL import Image
img = Image.open(image_path)
w, h = img.size
max_side = 2000
if w > max_side or h > max_side:
    scale = max_side / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # 增强对比度 + 锐化（RapidOCR对低对比度图片识别差）
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    img = img.filter(ImageFilter.SHARPEN)
    # 保存缩小版供OCR使用
```

关键：
- 阈值 `max_side=2000`（经验值，平衡速度与精度）
- 缩放算法用 `Image.LANCZOS`（高质量下采样）
- 保存到 `_resized.png` 临时文件，不影响原图
- 小图（<2000px）不触发，不影响正常使用

### ⚠️ LaTeX-OCR(pix2tex) 环境前提（2026-08-04 实测，重要）

**pix2tex 0.1.4 在新版 torch（≥2.9）环境不可用**——固定依赖 x-transformers==0.15.0（2022年）与新版 torch 不兼容，decoder 生成阶段输出乱码（GitHub issue #161/#241 同款，官方未修；官方 Dockerfile 只用 python3.8+torch>=1.7.1 验证）。**排查链确认模型/权重/预处理全正常、仅 decoder 乱码 = 版本兼容问题**（详见 xueba-platform-dev「公式识别评估」节）。

- 本机（Python 3.12 + torch 2.9.1）实测识别 "3x+6=18" 返回 `\mathcal{9}\chi\mp...` 完全错误 → **已卸载 pix2tex/x-transformers**，LaTeX-OCR 分支实际不可用。
- 修复需降级 torch 到 1.x（破坏其他项目依赖）或 Docker 老环境（生产 ECS 1.87G 内存扛不住）——**都不做，保持 RapidOCR + _fix_math_symbols 兜底**。
- 未来若重新启用：先 `pip show torch x-transformers` 确认版本；官方未适配新版 torch，替代路线是 ONNX 版公式识别模型（无 torch 依赖）。
- 双引擎策略（400px 阈值路由）代码保留但 LaTeX 分支静默失败——数学公式识别目前靠 `_fix_math_symbols` 三层纠错，已知短板（上标/减号）。

### 双引擎策略：LaTeX-OCR + RapidOCR（HEIGHT-AWARE路由）

**关键发现：LaTeX-OCR会把整页试卷当成一个公式来识别，输出乱码。** 必须根据图片大小路由引擎。

```python\n# 核心路由逻辑\nimg_pil = Image.open(image_path)\nw, h = img_pil.size\nis_large_image = w > 400 or h > 400  # ⚠️ 400px阈值（代码实际值agent_service.py:1010）\n\n# 小图（单道公式）→ LaTeX-OCR\nif not is_large_image:\n    latex_model = OCREngine._latex_model  # 全局单例缓存\n    if latex_model:\n        result = latex_model(PIL.Image.open(image_path))\n        if result and len(str(result)) > 5:\n            return result  # 返回LaTeX格式\n\n# 大图（整页试卷）→ RapidOCR 通用文字\nengine = OCREngine._engine  # 全局单例\nresult = engine(image_path)  # 返回文字+坐标框\n```\n\n- **阈值400px**（agent_service.py:1010）：单道公式照片通常<400px，整页试卷>400px\n- ⚠️ **已知问题**：大部分学生用手机拍的作业>400px，**直接跳过LaTeX-OCR**，数学公式识别为普通文字（如 `x²` 变成 `x2`），需依赖 `_fix_math_symbols` 三层纠错弥补\n- ⚠️ **不是设计缺陷，是性能取舍**：LaTeX-OCR处理大图会输出乱码（把整页当公式识别）\n- **优化方向**：未来可对>400px图片做**版面分析后切块**，每块<400px再走LaTeX-OCR\n- LaTeX-OCR首次加载约23秒（97MB权重），后续瞬时\n- LaTeX-OCR返回LaTeX格式（`x^{2}-5x+6=0`），保留数学结构\n- RapidOCR返回坐标框+文本，适合中文+公式混合场景\n- **实测教训**：3500×2500的8开试卷走LaTeX-OCR → 输出全部乱码（把整页当公式识别）\n- **正确做法**：先降采样→RapidOCR→`_fix_math_symbols`纠错→DeepSeek诊断

## 参考文件

- `references/math-ocr-correction-reference.md` — 完整正则表
- `references/math-correction-test-cases.md` — 22个完整测试用例（变量x/根号/上标/选项格式化）
- `references/ovisocr2-pipeline-integration.md` — **OvisOCR2 三级降级链集成（2026-08-02 已实施 · commit fdd85ec）**：无GPU部署配方（GGUF+mmproj+Ollama+hf-mirror）、调用代码、实测数据、陷阱清单；开发机走OvisOCR2，生产ECS无Ollama自动降级MinerU

## 视觉模型选型与视觉桥（2026-08-09 实测）

### MiniCPM-V 4.6 —— 选型结论：不进 OCR 降级链，备用

- 面壁智能/OpenBMB 开源（26K★），1.3B 端侧多模态；**Ollama tag 是 `minicpm-v4.6`**（不是 `minicpm-v:4.6`——后者不存在，会报 manifest 错误），1.6GB
- 实测（手写几何作业图）：63s/2059字，**会"理解性纠错"**——把学生手写的"O为AB为点"自动改成"中点"
- **选型原则（OCR 诊断场景）：忠实 > 理解。** 诊断引擎（DeepSeek 错因分析）必须拿到孩子"原样写的什么"，模型自动纠错反而掩盖真实错误 → ovisocr2（忠实+LaTeX+更快 54s）仍是一级本地引擎
- 价值定位（备用）：①本地数学题解答兜底（带思考推理）②通用视觉（视频/多图/物体定位）③官方免费 API 云端版（不占本地资源）

### ModLens —— 视觉桥 CLI（图片→结构化 JSON）

- 定位：给纯文本 LLM 补视觉的桥——输出 summary + ocr.full_text + layout.regions + semantics.entities
- **桥 ≠ 引擎**：ModLens 自己不识别，调配置的 provider。配火山方舟 = 还是花豆包的钱，不省钱；省钱的唯一方式是本地引擎（ovisocr2）提级
- 安装：`D:\工具\modlens`（`npm install --registry=https://registry.npmmirror.com` + `npm run build` → `dist/main.js`）；skill 已装 Hermes（company-skills/modlens）
- 零新增账号配置（复用火山方舟 openai 兼容端点）：
  ```
  node dist/main.js config set openai.baseUrl https://ark.cn-beijing.volces.com/api/v3
  node dist/main.js config set openai.apiKey <ARK_API_KEY>
  node dist/main.js config set openai.model doubao-seed-2-1-turbo-260628
  node dist/main.js config set provider openai
  ```
- 调用：`node D:\工具\modlens\dist\main.js -i <图路径>`；Windows 路径用 `D:/...` 正斜杠（`/d/...` MSYS 形式会被误拼为 `D:\d\...` 找不到文件）

### ⚠️ 大图对云端视觉 API 同样必须降采样

3114×1975 截图直接发豆包视觉（ModLens/直连 chat/completions）→ 读超时（>150s）；**降采样到 1600 宽后正常**。云端 API 与本地引擎一样受大图拖累——凡 >2000px 图，先 PIL LANCZOS 降采样再送识别（与本地 RapidOCR 的 max_side=2000 同一原则）。BMP 源先转 PNG（PIL convert RGB）。

## 扫描版 PDF 全量批量 OCR（2026-08-07 压轴题.skill 蒸馏实测，163 页）

扫描版教辅/教材（无文字层）批量 OCR 的可行参数（book-to-skill 的 scanned workflow 缺 Windows 实测细节）：

1. **pdftoppm 处理中文路径失败**：MSYS 下报 `I/O Error: Couldn't open file '/e/<八进制转义序列>...'`（中文路径编码问题）。**改用 PyMuPDF 渲染**：`doc[i].get_pixmap(dpi=150).save(f"p{i+1:03d}.png")`。
2. **RapidOCR 批量**：`from rapidocr_onnxruntime import RapidOCR`，每页结果 `(bbox, text, score)` → 取 `line[1]`；dpi=150 时约 **14 秒/页**（163 页 ≈ 37 分钟）——务必 `terminal(background=true, notify_on_complete=true)` 后台跑 + 每 10 页打印进度。
3. **输出格式**：`\n===== 第{i}页 =====\n` 分隔写 txt，便于按页定位；课/章标题正则 `第\s*(\d+)\s*课\s*([^\n]{2,22})` 从全文提取可完整还原目录结构（实测 37 课全命中）。
4. **读 OCR 结果**：txt 可能被 read_file 误判 binary → 用 python `errors='replace'` 读取。
5. **蒸馏落地**：目录/方法论从封面版权页+序言页 OCR 获得；正文每课取前 600 字（方法导语+例1）作章节素材，配合领域专业知识补全模型/公式——不要照抄 OCR 大段原文。
