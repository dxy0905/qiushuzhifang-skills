---
name: math-ocr-pipeline
description: |
  数学作业OCR识别+错因诊断管道。组合RapidOCR（通用文字）+ LaTeX-OCR（公式识别）+ DeepSeek（CLTA诊断），
  实现拍照→识别→拆题→诊断→评估全流程。适用于学霸基本法等AI数学辅导系统。
---

# Math OCR Pipeline — 数学作业识别诊断管道

## 架构

```
上传 → 图片预处理(降采样+对比度增强+锐化) → 引擎路由判断(≤400px走LaTeX-OCR)
  ├─ → LaTeX-OCR（公式识别）2-5s（仅≤400px小图，首次加载23s）
  └─ → RapidOCR（通用文字）1-2s → _fix_math_symbols → 逐题拆分 → DeepSeek CLTA诊断 → 综合评价 → 知识库
```

## 三引擎策略

| 引擎 | 用途 | 加载方式 |
|:-----|:------|:---------|
| **RapidOCR** (`rapidocr_onnxruntime`) | 通用文字识别（中文题干、数字、文字描述） | 懒加载，单例缓存 |
| **LaTeX-OCR** (`pix2tex.LatexOCR`) | 数学公式识别（√、²、±、分式、根式等） | 懒加载，首次23s，后续缓存；仅≤400px小图启用 |
| **DeepSeek API** | 错因诊断（CLTA框架 + 错因5分类） | 需配 DEEPSEEK_API_KEY；启动时设置环境变量 |

## 关键代码结构

### OCREngine 类（agent_service.py）

```python
class OCREngine:
    _engine = None      # RapidOCR 缓存
    _latex_model = None  # LaTeX-OCR 缓存

    def recognize(self, image_path):
        # 0. 图片预处理：降采样 + 对比度增强 + 锐化
        img_pil = Image.open(image_path)
        if max(w, h) > 2000:
            scale = 2000 / max(w, h)
            img_pil = img_pil.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
            enhancer = ImageEnhance.Contrast(img_pil)
            img_pil = enhancer.enhance(1.5)          # 对比度增强
            img_pil = img_pil.filter(ImageFilter.SHARPEN)  # 锐化
        
        # 1. 小图(≤400px)尝试 LaTeX-OCR
        is_small = w <= 400 and h <= 400
        if is_small:
            latex_model = self._get_latex_model()
            if latex_model:
                result = latex_model(img_pil)
                if valid: return result

        # 2. 大图/回退：RapidOCR
        engine = self._get_engine()
        result, elapse = engine(image_path)

        # 3. 后处理：数学符号纠错
        text = self._fix_math_symbols(text)
```

### 8开试卷降采样增强（关键！）

大图(>2000px)直接喂RapidOCR会超时/崩溃。必须预处理：

```python
from PIL import Image, ImageEnhance, ImageFilter

img = Image.open(image_path)
w, h = img.size
if w > 2000 or h > 2000:
    scale = 2000 / max(w, h)
    img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)        # 对比度增强（文字更清晰）
    img = img.filter(ImageFilter.SHARPEN)  # 锐化
    # 保存缩小版
    resized_path = image_path.replace('.png', '_resized.png').replace('.jpg', '_resized.jpg')
    img.save(resized_path)
    image_path = resized_path
```

**效果：** 3500×2500(9MP) → 2000×1428(2.9MP)，从25MB降到8MB，OCR不再超时。

**注意：** LaTeX-OCR 不应处理整页大图（会当成一个公式输出`\begin{array}...`乱码），阈值设为400px。`is_large_image = w > 400 or h > 400`

### 数学符号纠错（_fix_math_symbols）— 全量版

三层修复架构，按顺序执行：

**第1层：基本替换** — 精确字符串匹配
```
V/J → √, 士 → ±, != → ≠, <= → ≤, >= → ≥
~~ → ≈, ~= → ≈
兀/TT/n → π, △ → Δ
0/0 → %, °/° → %, 0/o → %
```

**第2层：全角符号转半角** — 全角数字/字母/运算符→半角
```
全角: ０-９ Ａ-Ｚ ａ-ｚ ＋－×÷＝＜＞（）．，
↓
半角: 0-9  A-Z  a-z  +-×÷=<>().,
```

**第3层：上下文正则修复** — 数学语境智能纠错
```
1. 数字间x→×        例: 5x3 → 5×3
2. 数字间中点→×    例: 3·5 → 3×5  (⚠曾因第1层直接删掉"·"导致bug)
3. 字母后2→²       例: x2 → x², x^2 → x², x3 → x³
4. 选项后加空格     例: A.√7 → A. √7
5. 变量x被识别为1   例: 1≤3 → x≤3  (受后顾断言保护的多位数不变)
6. 大写X→x          例: X≥0 → x≥0
7. √括号补全        例: √x+4 → √(x+4), √(x+4( → √(x+4())
8. 分数横线修复     例: --- 或 ___ → ─ (分数线)
9. 括号平衡         补全末尾缺失的右括号
10. 数字中点空格    例: 0. 01 → 0.01
```

**⚠️ 修复顺序陷阱（关键！）：**
- 第1层的精确替换必须在第3层正则之前执行
- 不要在基本替换中无脑删除"·"（会破坏第3层的中点乘号匹配）
- 全角转半角必须在第2层执行，否则第3层正则匹配不到全角符号
- "进步1）"修复必须在全角转半角之后（因为）→)）

完整替换表见 `references/ocr-math-symbol-fixes.md`

### 图片质量预检（check_image_quality）

OCR前先检测图片质量，避免低质量图片浪费时间和token：

| 检测项 | 方法 | 阈值 | 决策 |
|--------|------|------|------|
| 模糊度 | Laplacian 方差 | <100 → 模糊 | score≥50: continue, 20-50: warn, <20: reject |
| 亮度 | 灰度均值 | <30过暗, >220过曝 | |
| 对比度 | 标准差 | <20低对比度 | |

降级：`ImportError`（无numpy/scipy）或文件不存在时自动返回 continue，不阻断流程。

### 逐题拆分（split_into_problems）

```python
pattern = r'(?:^|\\n)\\s*(?:第[一二三四五六七八九十]题|[\\(（]?\\d+[\\)）]\\.?)'
# 按题号分割OCR文本为单题列表
```

### 综合评价（comprehensive_evaluation）

```python
{
    "total_problems": N,
    "correct_count": M,
    "error_count": N-M,
    "error_distribution": {"概念不清": 2, "计算失误": 1, ...},
    "score": "M/N",
    "grade": "优秀/良好/需努力"
}
```

### 知识库集成

错因模式入库（kb_add），供诊断参考：
```python
sm.kb_add(topic, error_type, error_pattern, correct_understanding, example_question, grade)
# 示例:
sm.kb_add("二次根式", "概念不清", "忽略被开方数必须≥0",
           "算术平方根要求被开方数≥0", "若√(x-3)有意义，求x的取值范围", "八年级")
```

查询接口：
- `POST /api/v2/knowledge/search` — 按知识点/错因类型搜索
- `POST /api/v2/knowledge/add` — 新增错因模式
- `GET /api/v2/knowledge/topics` — 查看所有知识点统计

## ⚠️ LaTeX-OCR(pix2tex) 环境前提（2026-08-04 实测，重要）

**pix2tex 0.1.4 在新版 torch（≥2.9）环境不可用**——固定依赖 x-transformers==0.15.0（2022年）与新版 torch 不兼容，decoder 生成阶段输出乱码（GitHub issue #161/#241 同款，官方未修；官方 Dockerfile 只用 python3.8+torch>=1.7.1 验证）。排查链确认模型/权重/预处理全正常、仅 decoder 乱码 = 版本兼容问题（详见 xueba-platform-dev「公式识别评估」节）。

- 本机（Python 3.12 + torch 2.9.1）实测识别 "3x+6=18" 返回 `\mathcal{9}\chi\mp...` 完全错误 → **已卸载 pix2tex/x-transformers**，LaTeX-OCR 分支实际不可用。
- 修复需降级 torch 到 1.x（破坏其他项目依赖）或 Docker 老环境（生产 ECS 1.87G 内存扛不住）——**都不做，保持 RapidOCR + _fix_math_symbols 兜底**。
- 未来若重新启用：先 `pip show torch x-transformers` 确认版本；官方未适配新版 torch，替代路线是 ONNX 版公式识别模型（无 torch 依赖）。
- 双引擎/三引擎策略的 ≤400px LaTeX 分支代码保留但静默失败——数学公式识别目前靠 `_fix_math_symbols` 三层纠错，已知短板（上标/减号）。

## LaTeX-OCR 权重安装

```bash
# 权重 97MB，首次自动下载
# 如网络超时（国内常见），手动搬运：
mkdir -p ~/.pix2tex
# 从GitHub Releases下载到 ~/.pix2tex/weights.pth
# 然后复制到pix2tex包目录：
python3 -c "
import pix2tex.model, os, shutil
ckpt = os.path.join(os.path.dirname(pix2tex.model.__file__), 'checkpoints')
os.makedirs(ckpt, exist_ok=True)
shutil.copy2(os.path.expanduser('~/.pix2tex/weights.pth'), os.path.join(ckpt, 'weights.pth'))
"
```

**镜像备选：** `hf-mirror.com/lukas-blecher/pix2tex/resolve/main/weights.pth`

### OCR质量校验（三级置信度）

```python
@staticmethod
def _check_ocr_quality(text: str) -> dict:
    \"\"\"OCR质量校验：三级置信度输出\"\"\"
    if not text or len(text.strip()) < 5:
        return {"quality": "low", "score": 0, "issues": ["识别结果为空或过短"], "decision": "skip"}
    
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())
    chinese_ratio = chinese_chars / max(total_chars, 1)
    issues = []
    
    if chinese_ratio < 0.05 and total_chars > 10:
        issues.append("中文字符占比过低，可能是识别错误")
    if total_chars < 10:
        issues.append("识别文字过短，可能未正确拍摄")
    if text.count('\ufffd') > 5:
        issues.append("存在大量乱码字符")
        
    score = min(100, int(chinese_ratio * 50 + min(1, total_chars / 100) * 30 + (0 if issues else 20)))
    if score >= 50 and not issues:        # high → auto
        quality, decision = "high", "auto"
    elif score >= 20:                     # medium → review
        quality, decision = "medium", "review"
    else:                                 # low → skip
        quality, decision = "low", "skip"
        
    return {"quality": quality, "score": score, "issues": issues, "decision": decision}
```

**三级决策：** 高(≥50,无问题)→自动出诊断 / 中(20-49)→建议人工复核 / 低(<20)→提示重拍。

### 多后端OCR配置

学霸基本法支持多个OCR后端，通过 `ocr_with_backend()` 自动路由：

| 后端 | 需要 | 状态 |
|:-----|:------|:-----|
| RapidOCR (本地) | 无 | ✅ 默认激活 |
| MinerU (本地) | `pip install mineru` | ✅ 已安装 |
| 百度Unlimited-OCR (云端) | BAIDU_OCR_API_KEY | ✅ 已配置 |
| Mistral OCR (云端) | MISTRAL_API_KEY | ⏳ 需VPN |
| 豆包 doubao-seed-2-1-turbo-260628 (云端) | 火山方舟 API Key | ✅ 生产一级（2026-08-08 接入，端点 ep-20260808211150-zzsbs）|
| OvisOCR2 (本地 Ollama) | 无 | ✅ 生产二级降级 |
| MiniCPM-V 4.6 (本地 Ollama, 1.6GB) | 无 | ⏸ 备用，不进降级链（见下方选型原则）|

### 诊断场景 OCR 引擎选型原则（2026-08-09 三方实测）

**「忠实原文 > 理解性纠错」**——诊断引擎做错因分析必须拿到学生**原样写的字**，任何"智能修正"都会导致误判：

| 引擎 | 手写几何作业实测 | 判定 |
|:-----|:----------------|:-----|
| 豆包 doubao（云端）| ~135s；最全：LaTeX 公式、**识别图注**（"第1题图标注A/M/B/D/C"）、数学符号准确（A'D' 非 A'D）| ✅ 一级 |
| OvisOCR2（本地）| 54s；忠实保留原文（"O为AB为点"原样输出，不"修正"）| ✅ 二级（快+忠实）|
| MiniCPM-V 4.6（本地）| 54s；内容全（1907字）但**理解性纠错**："写错笔记本上"被读成"写在错题笔记本上"、"点0恰为AB中的点"被"修正"| ❌ 不进诊断链 |

**教训：** 通用视觉模型（MiniCPM 类）擅长"理解图像语义"，但这种能力在 OCR 诊断场景是**缺陷**——学生写错的字被美化，诊断引擎拿到错误文本会误判（违反"宁可复核不可误判"铁律）。通用视觉模型适合"看图表/理解场景"（如 ModLens 结构化摘要），不适合"逐字转录"（诊断输入）。选择 OCR 引擎先明确用途：**转录要忠实，理解才要智能**。

详见 `references/multi-backend-ocr-config.md`；豆包 OCR 接入方案见 `references/doubao-ocr-接入方案.md`。

## 常见问题

### 首次调用慢
LaTeX-OCR首次加载23s（模型初始化），第二次开始秒级响应。用单例模式缓存。

### OCR结果乱码
RapidOCR对手写体/印刷体的√、²、x、≤等符号识别率低 → `_fix_math_symbols`修复。
对电脑生成的PIL图片识别更差 → 建议用真实手机拍照。

### 8开试卷读不了
原因：3500×2500大图喂RapidOCR导致超时/崩溃。
修复：自动降采样到2000px以内 + 对比度增强 + 锐化。

- **DeepSeek API 未配置**
启动时需设置 `DEEPSEEK_API_KEY` 环境变量，否则AI诊断不可用。

### DeepSeek-V4 Flash 逐题批改诊断

诊断流程已升级为**逐题批改 + 知识库注入 + 苏格拉底追问**模式：

```
OCR识别文本 → DeepSeek-V4 Flash 逐题判断对错
                ↓
        每题输出：题号、正误、学生答案、正确答案、概念名、错因分析、追问问题
                ↓
        前端显示在「诊断分析」面板 + 自动生成练习题
```

#### 后端关键配置

```python
# agent_service.py
self.model = "deepseek-v4-flash"  # 不是 deepseek-chat!
```

#### 诊断Prompt架构（2026-07-12优化版）

CLTA_DIAGNOSE_PROMPT 采用四段式结构，约1777字符：

| 段落 | 功能 | 作用 |
|------|------|------|
| **一、推理步骤** | 内部思考链 | 要求LLM先推理后输出：逐题判断→定位具体概念→区分类别→设计追问 |
| **二、错因分类定义** | 6类表格+判断标准 | 每类有含义+判断条件，避免LLM胡乱分类 |
| **三、输出JSON格式** | 严格模板 | 含concept_name/follow_up_question/error_distribution/summary/verdict |
| **四、注意事项** | 约束规则 | 概念名必须具体、区分概念vs运算、苏格拉底追问 |

**关键字段说明：**

| 字段 | 说明 | 约束 |
|------|------|------|
| `concept_name` | 具体知识点概念名（如"二次根式被开方数非负性"） | 禁止只写"概念不清" |
| `error_type` | 6类枚举：概念不清/方法不当/步骤不完整/审题不仔细/迁移不足/运算错误 | 必须匹配判断标准 |
| `error_analysis` | 具体错在哪一步、什么概念没掌握 | 需含具体概念名(30-80字) |
| `follow_up_question` | 苏格拉底式追问，引导学生自己发现错误 | 不直接给答案(15-30字) |
| `summary.verdict` | 1-2句话整体判断 | 概括学生主要问题 |

**Prompt模板陷阱（两个必须注意！）：**

1. **花括号冲突** — JSON花括号会与Python `.format()` 冲突，必须用 `.replace()`：
```python
# ❌ 错误
prompt = CLTA_TEMPLATE.format(text=text)  # KeyError
# ✅ 正确
prompt = CLTA_TEMPLATE.replace("{text}", text)
```

2. **history_hint 未注入的 bug** — 知识库查询了 `matched = session_manager.kb_search()` 构建了 `history_hint` 但忘记注入 prompt：
```python
# ❌ 错误 — history_hint 被丢弃
prompt = CLTA_DIAGNOSE_PROMPT.replace("{text}", text)
# ✅ 正确 — 同时注入 text 和 history_hint
prompt = CLTA_DIAGNOSE_PROMPT.replace("{text}", text).replace("{history_hint}", history_hint)
```
检查点：所有调用 CLTA_DIAGNOSE_PROMPT 的地方（`diagnose` + `diagnose_stream`）都必须有 `.replace("{history_hint}", ...)`。

#### 错因6分类定义速查

| 类型 | 含义 | 判断标准 |
|------|------|---------|
| 概念不清 | 对概念/定理/公式本质不理解 | 用错公式、混淆定义、忽略条件 |
| 方法不当 | 知道概念但解题策略错 | 选错路径、设错未知数、辅助线方向错 |
| 步骤不完整 | 缺少关键步骤 | 跳步、没验证、分类讨论不完整 |
| 审题不仔细 | 误读/漏看条件 | 抄错数、看错符号、忽略隐含条件 |
| 迁移不足 | 能做标准题但变式不会 | 条件一变就卡住 |
| 运算错误 | 理解方法正确，仅计算过程错 | 去括号符号错、移项忘变号、合并算错 |

#### 前端显示逻辑

`showDiagnosis()` 函数从API响应的 `data.per_question` 数组读取逐题数据渲染：

```javascript
var perQ = data.per_question || [];
// 对每道题显示 ✅/❌ + 学生答案 + 正确答案 + 错因分析 + 错因类型标签
```

⚠️ **注意：** `errList`（error_types）部分如果使用 `=` 赋值会**覆盖** `per_question` 的HTML。必须用 `+=` 追加：

```javascript
// ❌ 错误：覆盖了逐题批改结果
analysisHtml = '<div>错因汇总</div>';

// ✅ 正确：追加到逐题批改之后
analysisHtml += '<div>错因汇总</div>';
```

### 端口占用冲突
旧进程（PID 5496）顽固占用8000端口时，改端口8001启动。
配置：修改 `main.py` 中 `port=8001`。访问 `http://127.0.0.1:8001`。

**Windows幽灵进程现象：** `netstat` 显示PID但 `taskkill /F /PID` 杀不掉（可能是Docker/WSL网络代理）。尝试 `wsl --shutdown` 释放端口。如果仍不行，直接用8001端口。

### showConfirmArea空指针
**症状：** 诊断完成时报 `Cannot set properties of null (setting 'disabled')`
**原因：** DOM布局变动后 `.confirm-btn` 元素不存在。
**修复：** 加null安全检查：
```js
var btn = area.querySelector('.confirm-btn');
if (btn) { btn.disabled = false; btn.textContent = '已理解，继续'; }
```
