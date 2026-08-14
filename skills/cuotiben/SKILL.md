---
name: cuotiben
description: |
  错题本工具包 — 错题录入/分类/诊断/复习/盲区分析/组卷打印全流程。
  基于学霸基本法技术栈，集成OCR识别+CLTA错因诊断+知识库+定时推送。
  配置：教育部全体员工。
---

# 错题本 · 工具技能

## 五步法（最佳实践）

| 步骤 | 核心 | 学霸基本法实现 |
|:-----|:------|:--------------|
| ① **收集** | 拍照/批量导入，成本趋零 | LaTeX-OCR + RapidOCR → 自动拆题 |
| ② **分类** | 按错因5分类法归类 | CLTA诊断 + 知识库自动归类 |
| ③ **诊断** | 具体概念名+缺失步骤+追问引导+变式 | DeepSeek + CLTA框架 |
| ④ **复习** | **Bjork间隔提取（1天→3天→7天→21天→归档）** | localStorage错题本 + showErrorBook()面板 |
| ⑤ **盲区分析** | 知识点分布×错因频率×错误趋势 | type_stats统计 + 知识库分析 |

## Bjork间隔提取（2026-07-13 实战升级，替代原艾宾浩斯方案）

基于认知科学文献，从原来的艾宾浩斯（1-3-7-月考）升级为更精准的 Bjork 间隔提取（1-3-7-21）：

| 时间 | 动作 | 产品化 |
|:-----|:------|:-------|
| 第1天 | 遮挡订正 | 诊断后立即做 |
| 第3天 | 第一次盲做 | 错题本面板标红提醒 |
| 第7天 | 第二次盲做 | 错题本面板标红提醒 |
| 第21天/考前 | 最终消灭 | 归档「已掌握」 |

### 存储实现（localStorage）
```javascript
book[key] = {
  concept: 知识点名称,
  error_type: '概念不清',
  analysis: '出错分析',
  stage: 0,         // 0-3
  next_review: timestamp, // 下次复习时间
  correct_count: 0,
  active: true
}
```

### 前端面板
`showErrorBook()` 函数：按 next_review 排序，过期标红背景 `#fff0f0`，四个操作按钮（🔄遮挡重做/✅已掌握/🤔还糊涂/📦归档）。每次点击「已掌握」自动推进 stage 并计算下一复习时间。

### 还糊涂标记（2026-08-04 新增 · 博文《辅导作业别吼了》启示3）
**"已搞懂/还糊涂"二分 + 周末复盘"糊涂优先"过滤：**
- `markErrorConfused(key)`：标记 need_review=true + stage重置0 + correct_count清零 + next_review=now（立即回到待复习）
- 排序升级：**还糊涂 > 过期待复习 > 未到期**；两个都糊涂时按到期急迫度排序
- 卡片显示红色 `🤔 还糊涂` 徽标 + `‼ 待再讲`，红色边框 #ff8a80 高亮
- 「✅已掌握」时自动清除 need_review 标记
- 周末复盘建议：只复习"还糊涂"的题（排最前），懂了打勾，糊涂的重讲

### 遮挡重做（路径E）
从错题本点击「🔄遮挡重做」→ 只显示原题描述（不显示答案和学生解答）→ 学生在纸上写 → 拍照上传 → AI对比批改。三步骤引导：写过程→拍照→AI批改。

## 错题集功能（2026-07-08新增 · 2026-07-20更新：端口修正+Server启动流程+零数据处理）

### API

```bash
POST /api/v2/review/generate
{"period": "week", "topic": "", "error_type": "", "limit": 20}
# period: week | month | semester
# 返回: period_label, total, selected, cards[], type_stats{}, review_html, pdf_base64
```

**实际运行的API端口：8000**（由 `start_server.py` 启动的 uvicorn 实例，host=0.0.0.0 port=8000）。勿使用8080端口——旧版已废弃，且存在端口幽灵进程问题（见 `references/windows_port_ghost.md`）。

### 定时推送（cronjob）

- **每周一 09:00** → `错题集 · 每周推送`
- **每月1日 09:00** → `错题集 · 月度推送`

**Server启动检查（cronjob必须步骤）：**
1. 先检查 server 是否运行：`curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health --connect-timeout 3`
2. 若返回非200（服务未运行），用 `terminal(background=True)` 启动：
   ```bash
   cd /d/邱数智方/项目/学霸基本法 && python start_server.py
   ```
3. 等待3-5秒后确认服务已就绪再发起API请求
4. 若使用 Hermes cron Agent 模式（非内嵌Python），API调用可用 `terminal("python -c ...")` 直接执行简单单行脚本（2026-07-27 验证通过），复杂脚本走 `write_file`(写临时py脚本到 `.hermes/tmp/`) → `terminal`(运行) → cleanup三步法。`execute_code` 在cron模式被安全策略阻止。

**零数据（total=0）处理：** 当本周无错题记录时，API仍返回完整的HTML模板（内容为"共0道高频错题"）。此时：
- 正常保存HTML存档（文件约1KB，含样式+打印按钮+零数据提示）
- 报告中应明确标注「本周无高频错题记录」而非跳过
- 零数据本身是有意义的信号（可能是学生未使用平台/错题数据未录入/本周无错误）

**存档路径：**
```
D:\邱数智方\项目\学霸基本法\错题集\weekly_{YYYYMMDD}.html
```
必须使用原生Windows路径（`D:\...`），MSYS路径（`/d/...`）在Python的`os.makedirs`中可能创建错误目录层级。

### 前端入口
- 左栏绿色 `[错题集]` 按钮 → 弹窗选时间 → 生成 → 下载/打印

## OCR管道架构

### 管道V1（旧）：RapidOCR + LaTeX-OCR
- **大图（>400px）** → RapidOCR通用文字识别
- **小图（≤400px）** → LaTeX-OCR公式识别
- **超大图（>2000px）** → 降采样+对比度增强(1.5x)+锐化

### 管道V2（2026-07-18）：MinerU 统一解析（支持PDF+图片）
**文件**: `server/services/ocr_pipeline.py`

MinerU 3.4.0 已安装，作为统一的文档解析入口。自动适配文件类型：

| 文件类型 | MinerU参数 | 用途 |
|----------|-----------|------|
| PDF | `--method auto --backend pipeline` | 试卷、文档 PDF 解析 |
| 图片 | `--method ocr --backend pipeline` | 拍照作业图片 |

**管道流程**:
```
用户上传 (图片/PDF)
  ↓ MinerU 解析（180秒超时）
  ↓ 读取 .md / .json / .txt 输出
  ↓ 逐题拆分 → DeepSeek V2.1诊断 → 综合评估
  ↓ 返回 JSON 结果
  ↓ 如果 MinerU 产出不足（<20字符）→ 自动回退 RapidOCR
```

**诊断入口**: `POST /api/v2/ocr/enhanced`（multipart上传，支持 .pdf/.jpg/.png/...，20MB上限）

**关键实现**:
```python
def mineru_parse(file_path):
    ext = get_ext(file_path)
    if ext == ".pdf":
        cmd = ["mineru", "-p", file_path, "-o", output_dir, "--method", "auto", "--backend", "pipeline", "-l", "ch"]
    else:
        cmd = ["mineru", "-p", file_path, "-o", output_dir, "--method", "ocr", "--backend", "pipeline", "-l", "ch"]
    result = subprocess.run(cmd, timeout=180, capture_output=True, text=True)
```

**回退机制**: MinerU 无输出时 → 调用 `OCREngine.recognize()`（RapidOCR）

### 数学符号纠错（_fix_math_symbols）
V→√, J→√, <=→≤, >=→≥, !=→≠, 1→x(不等式上下文), X→x(数学上下文), x2→x², A.√7→A. √7, √x+4→√(x+4), 0. 01→0.01

### 质量校验（_check_ocr_quality）
自动检查中文比例≥5%、文字长度≥10、无乱码 → pass/warn/fail

## 错因5分类法

1. **概念不清** (~35%) → 回归课本
2. **审题不仔细** (~20%) → 圈关键词训练
3. **步骤不完整** (~20%) → 规范答题模板
4. **公式记错** (~15%) → 推导记忆法
5. **迁移不足** (~10%) → 变式训练

## 逐题诊断格式（2026-07-09 · v7两步诊断版）

诊断提示词 `CLTA_DIAGNOSE_PROMPT_TEMPLATE` 要求 DeepSeek 按**两步法**输出：

### 第一步：整体判断
先列出每题的对错清单：
```
- 第1题：✅ 正确（√3是最简二次根式）
- 第2题：❌ 错误（√20可化简为2√5，不是最简）
- 第3题：❌ 错误（x≥5写成了x=-3）
```

### 第二步：逐题详细分析
每道题按以下格式输出：
```
【第X题】
1. 题号：第X题
2. 正误：✅ 做对了 / ❌ 做错了
3. 学生答案：学生写了什么
4. 正确答案：应该是什么
5. 具体错在哪：精确到哪个数字/符号/步骤
6. 错因类型：从5类中选择
   - 概念不清 → **必须写具体概念名，如"二次根式的被开方数≥0这个概念没掌握"**
   - 方法不会选 / 步骤不完整 / 审题不仔细 / 迁移不足
7. 详细说明：推理链条在哪断了，**要区分是"概念没掌握"还是"运算没学会"**
```

**核心要求：** ①先整体再逐题 ②禁用"概念不清"四字，必须写具体知识点 ③每题【第X题】标注

### 诊断提示词 V2.1（2026-07-18）— 几何证明专项 + corrective_guidance
升级版 `CLTA_DIAGNOSE_PROMPT` 新增三大改进：

**① 几何证明专项检测**：检查学生是否根据题意写对了"已知"、"求证"、"证明"的三段式规范。区分"判定定理"与"性质定理"的混用。

**② per_question 新增 corrective_guidance 字段**：每题给出具体行为指导，如"严格遵循已知→求证→证明的三段式书写规范"。

**③ 顶层新增 corrective_guidance_list 字段**：1-3 条综合性纠正指导，如"建议后续严格遵循已知→求证→证明的三段式书写规范，落实步步有据的推理习惯；同时通过变式训练厘清判定与性质的逻辑先后顺序"。

**关键注意事项（V2.1）**：
- 对于几何证明题，务必检查学生是否写出了正确的"已知"
- corrective_guidance 必须写具体的"怎么做"（行为要求），而非笼统的"需要加强"
- max_tokens 从 4096 提升至 8192，防止多题几何分析被截断
- 主力模型从 Agnes AI 切回 DeepSeek（provider="deepseek"），后者输出完整稳定

## 三级置信度机制（2026-07-08新增）

博文 `local-grading-automation` 启示，诊断结果需带置信度判断：

| 级别 | 分值 | 决策 | 前端标签 | 含义 |
|:----:|:----:|:-----|:---------|:------|
| **high** | ≥50 | auto | 🟢 高置信度 | 直接出诊断，无需复核 |
| **medium** | 20-49 | review | 🟠 建议复核 | AI不确定，标给教师看 |
| **low** | <20 | skip | 🔴 置信度低 | 提示重拍或人工批改 |

### 实现位置
- OCR质量校验：`agent_service.py::OCREngine._check_ocr_quality()`
- 诊断置信度：`agent_routes.py` 的 `/api/v2/diagnose/analyze` 返回 `confidence` + `data-confidence` 字段
- 前端展示：`app.js::showDiagnosis()` 读取 `data-confidence` → 渲染绿/橙/红标签

### 置信度计算规则
```
score = chinese_ratio * 50 + min(1, chars/100) * 30 + (无问题奖励20)
high: score≥50 且无问题 → auto
medium: score≥20 → review
low: 其他 → skip
```

## 关键教训（博文启示）

1. **方向错了修bug是最大浪费** — 先验证方向再深入编码
2. **小细节决定工具能不能用** — 符号显示/打印布局决定成败
3. **知道什么叫能用** — 每个环节需设立质量标准
4. **迭代开发节奏** — 每次只改一个位置/功能 → 让用户确认 → 再继续。布局迭代见 references/layout_lessons.md
5. **数据持久化优先** — IndexedDB存诊断记录+聊天历史，防止刷新丢失

## 数据持久化（IndexedDB）

关闭页面后诊断/聊天记录丢失是用户最大痛点。前端已实现IndexedDB存储层：

```javascript
var DB_NAME = 'XueBaDB';
var DB_VERSION = 1;
function openDB() { /* 创建/打开IndexedDB，含records表+timestamp索引 */ }
function saveRecord(data) { /* 存诊断/OCR/聊天记录 */ }
function loadRecords(limit) { /* 读取最近N条记录 */ }
```

存储时机：OCR完成、诊断完成、聊天发送时各存一次。

## Token节省策略

详情见 references/token_saving.md。核心策略：

| 方法 | 实现 | 节省 |
|:-----|:------|:----:|
| Prompt压缩 | `_compress_prompt()` 去敬语/缩写/去空格 | 15-25% |
| 知识库缓存 | 已有结果不重复请求DeepSeek | 30-50% |
| 模型选择 | DeepSeek Chat（性价比最优） | - |
| OmniRoute网关 | 231个Provider + RTK+Caveman压缩 | 15-95% |

`_compress_prompt()` 方法：
```python
def _compress_prompt(self, text: str) -> str:
    text = re.sub(r' +', ' ', text)           # 多空格→单空格
    text = re.sub(r'\n{3,}', '\n\n', text)     # 多空行→双空行
    text = text.replace('请', '').replace('您', '你')  # 去敬语
    text = text.replace('首先','1)').replace('其次','2)')
    text = text.replace('最后','3)').replace('综上所述','')
    text = text.replace('例如','如').replace('也就是说','即')
    return text.strip()
```

## 已知限制与规避

| 限制 | 规避 |
|:-----|:------|
| RapidOCR读不懂电脑生成字体 | 必须用真实拍照/扫描图片 |
| LaTeX-OCR加载慢（首次23s） | 单例缓存，后续即时 |
| 大图base64传输慢 | 后端自动降采样到2000px |
| 诊断结果关闭丢失 | IndexedDB持久化（见上） |
| 幽灵进程占8000端口 | `start_server.py` 用单实例锁（`.server_pid`）预防重复启动；端口冲突时改 `port=8001` 临时切换（见 `references/windows_port_ghost.md`） |
| 空指针：confirm-btn不存在 | 加 `if (btn) { ... }` 保护 |

## 设计哲学（源自local-grading-automation博文）

### 1. AI不替人拍板
三级置信度机制确保AI只做确定的部分，难的部分留给人：
- **high(≥50)** → 自动出诊断（绿标）
- **medium(20-49)** → 暂停标"建议复核"（橙标）
- **low(<20)** → 提示重拍或人工批改（红标）

### 2. 显式启用（点火确认）
诊断流程需要用户主动点击"开始诊断"才触发，不会自动运行。用户有控制感。

### 3. 事件驱动流水线
上传→OCR→拆题→诊断→评估，每一步完成后自动触发下一步，任一环节可中断/重试。

### 4. 本地优先
所有处理在127.0.0.1本地完成，数据存本地SQLite，不暴露公网。

## API接口

| 端点 | 方法 | 用途 |
|:-----|:-----|:------|
| /api/v2/ocr/recognize | POST | OCR识别（含三级置信度） |
| /api/v2/diagnose/analyze | POST | 错因诊断（含confidence字段） |
| /api/v2/knowledge/topics | GET | 知识点列表 |
| /api/v2/knowledge/search | POST | 知识库检索 |
| /api/v2/practice/generate | POST | 组卷练习 |
| /api/v2/review/generate | POST | **生成错题集（返回review_html + pdf_base64）** |

### 错题集PDF下载（2026-07-09新增）

`_render_review_pdf()` 用 reportlab 生成PDF，Base64编码后返回给前端。

**流程：**
1. 前端点击[错题笔记] → `POST /api/v2/review/generate`
2. 后端返回 `{ review_html, pdf_base64 }`
3. 前端显示「📥 下载PDF」按钮 → `data:application/pdf;base64,{pdf_base64}`
4. 学生可直接下载PDF打印

**字体：** Windows `simsunb.ttf`（宋体加粗），回退 `Helvetica`

### 📱 手机分享链接（2026-08-04新增 · 博文启示1落地）

**API：**
```bash
POST /api/v2/share/create   # 登录态调用，body: {title, cards:[{topic,error_type,error_pattern,correct_understanding,example_question}]}
# 返回: {token, url:"/share/{token}", expires_in_hours:24}
GET /share/{token}          # 免登录(白名单)，渲染移动端分享页，24h过期(410)，不存在404
```

**分享页特性（突出特色）：**
- KaTeX 本地渲染公式（/static/katex/，无CDN依赖）——**识别时是LaTeX、展示时也是LaTeX，全链路闭环**
- 错因5类分布条形图（概念不清/审题不仔细/步骤不完整/公式记错/迁移不足 各自颜色）
- 移动端响应式（max-width:640px，家长手机直接打开）
- 数据存 DB `share_links` 表（token 32位随机、24h过期、只读）

**前端入口：** 错题集弹窗 →「📱 手机分享」按钮 → 收集 localStorage 错题本 → 生成链接 + 复制按钮（navigator.clipboard + fallbackCopy 降级）

**坑：**
- `_html`/`sqlite3` 必须在 agent_routes.py **模块级** import（文件里原有函数级 import 会导致新路由 NameError）
- 分享页所有文本区（topic/pattern/correct/example）都要加 `math` class 才会被 KaTeX 处理
- 数据字段兼容：topic/concept/question_text、correct_understanding/correct_answer/explanation 多字段名兜底

## 点火确认机制（2026-07-09新增）

博文 `local-grading-automation` 启示，用户需主动点击"开始诊断"才触发AI：

```
上传图片 → OCR识别显示文本 → 显示🚀开始诊断按钮 → 用户点击 → 执行诊断
```

**实现：** `app.js` 中 `performOcr`成功回调改为显示 `startDiagnosis(ocrResult)` 函数，不再自动调用 `performDiagnosis`。

### 诊断输出目标（2026-07-09修改）

诊断结果写入**知识点归纳tab**（`rtab-kg`），不再写入错因分析面板（`rtab-errors`）：

```javascript
function showDiagnosis(data) {
  kgPanel.innerHTML = analysisHtml + kgHtml;  // 诊断+知识点合并显示
  switchRtab('kg');  // 自动切到知识点归纳tab
}
```

### 品牌命名规则（2026-07-09用户明确要求）

- ✅ **禁用"AI老师"** — 用户明确说"千万不要这样写，否则效果直接减半"
- ✅ **必须用"您的老师"** — 拟人化、尊重感
- ✅ **老师必须有真实照片** — 不能是机器人/emoji/文字
- ✅ **外貌/声音分开选择** — 先从性别选，再弹窗选具体

## LLM提供商配置

### DeepSeek（默认/主力）
```
LLMClient(provider='deepseek')
api_key: DEEPSEEK_API_KEY
base_url: https://api.deepseek.com/v1
model: deepseek-v4-flash
```
**主力模型切换教训（2026-07-18）**：agent_routes.py第85行曾硬编码 `provider='agnes'`，导致 Agnes AI 输出不稳定且常被截断（finish_reason=length）。改回 `provider='deepseek'` 后输出完整（finish_reason=stop）。遇到诊断截断，先查 provider 配置。

### MiniMax（免费50亿Token备选）
```
LLMClient(provider='minimax')
api_key: MINIMAX_API_KEY → fallback DEEPSEEK_API_KEY
base_url: https://api.minimax.io/v1
model: MiniMax-M3
```

### Qwen Cloud / DashScope（2026-07-18配置）
已在 `~/.hermes/config.yaml` 加入 Qwen Cloud 提供商配置：
```
qwen-cloud:
  api_key: ''  # 需设置 DASHSCOPE_API_KEY 环境变量
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  models:
    qwen3.6-plus: {}
```
**免费使用方式**: `hermes model` → 选择"Nous Portal" → 浏览器登录 OAuth（限时免费 Qwen 3.6 Plus）

## 后端API修复记录

### api_v2 错误消息修复（2026-07-18）
**问题**: `api_v2()` 在错误时也返回 `message="ok"`，前端显示"注册失败：OK"
**修复** (agent_routes.py `api_v2()`):
```python
def api_v2(data=None, code=0, message="ok"):
    if data is None: data = {}
    if code != 0 and message == "ok" and data.get("error"):
        message = data["error"]
    return JSONResponse(content={"code": code, "data": data, "message": message})
```

### 注册接口短信验证码校验（2026-07-18）
**问题**: `POST /api/v2/user/register` 接收 `code` 参数但从未验证。直接注册成功。
**修复**: 注册前调用 `verify_code(phone, code)` 校验，验证失败返回 401。
**同时修的前端bug**: `app.js` 中 `finishReg()` 读取了 `code` 但未传入请求体。需在 `body: JSON.stringify({...})` 中加 `code: code`。

## BKT 贝叶斯知识追踪（2026-08-04 P0 正式落地）

**文件**：`server/services/knowledge_graph.py`（BKTTracker 类）
**表**：`bkt_probs`（student_id + knowledge 联合主键，probability/answer_count/correct_count）
**参数**：initial_p=0.30, learn_rate=0.15, guess=0.15, slip=0.10, mastery=0.85, forget=0.02
（learn_rate 用 0.15 而非设计文档的 0.60——0.60 会导致两次全对即掌握 0.99，无区分度；0.15 下 对→0.757、连对→0.953 mastered、答错→0.626，行为合理）

**API**：
```bash
POST /api/v2/knowledge/bkt/update   # {user_id, knowledge, correct} → 贝叶斯更新
GET  /api/v2/knowledge/bkt/all?user_id=x  # 全部知识点掌握度(升序)
GET  /api/v2/knowledge/bkt/weak?user_id=x # 薄弱点TopN(未掌握且概率最低)
```

**前端联动（app.js）**：
- 诊断完成 → `reportBKTFromDiagnosis()` 逐题上报对错 + **有错题自动推送同类变式**（showPracticePaths + AI消息提示）
- 练习答题 `selectOption()` → 练对 bktReport(true)+错题本 markErrorCorrect；练错 bktReport(false)+markErrorConfused（还糊涂）
- 掌握度展示：我的目标页 `masteryPanelHtml()`（进度条：绿≥85% 蓝≥50% 橙<50%）+ 错题本卡片掌握度条
- `_practiceTopic` 记录当前练习知识点（showPracticePaths 时设置）

**验证数据**（test001 勾股定理）：对(0.30→0.757) 对(0.742→0.953 mastered) 错(0.934→0.626)

**坑**：
- bkt 上报用 `safeFetchJson` 静默 catch（不阻塞诊断流程）
- 前端 `loadBKT` 60秒缓存（_bktCache），错题本/目标页共用
- 知识点名超50字符截断（防滥用）

## 学习页布局定稿（2026-08-04 邱董确认"就这样"· 左、右对称）

```
顶部导航: 学习主页 | 错因分析 | 我的老师 | 📊掌握度 | 我的目标
左栏: 资料清单 | 课前预习 | 学习建议     ← 左栏功能完整(资料+预习+建议)
      文件列表 → 老师悬浮卡片(头像+名字+情绪+⚙️我的老师) → 底部按钮(上传/拍照/增强/错题笔记+红点徽标)
中间栏: 上传预览区/课前预习窗口 + 聊天区
右栏: 诊断分析 | 错因分析 | 测试练习      ← 右栏专注诊断三件套(诊断/错因/练习)
      内容: rtab-kg / rtab-errors(错题本也在此) / rtab-practice
折叠: 左栏⟨按钮 右栏⟩按钮 (toggleLeftCol/toggleRightCol)
```

**关键规则（邱董拍板，勿改）：**
- 界面文字**禁写"AI老师/AI教师"**，统一"老师/我的老师"
- 课前预习必须在左栏（学习建议对调事件教训：对调后左栏丢课前预习被邱董纠正）
- 学习建议按钮在左栏（点击→右栏显示 suggestion 内容，跨栏跳转）
- 错因分析在右栏（中间栏已删除；showErrorBook 自动 switchRtab('errors')）
- 综合评价圆徽：优=绿圈#2e7d32 / 良=黄圈#f9a825(深字#5d4037) / 差=红圈#c62828，阈值 85%/60%、70%/50%，+期末目标差距

## 版本迭代记录
| 日期 | 版本 | 变更 |
|:-----|:----|:------|
| 07-08 | v1 | 错题集API + cronjob + 三级置信度 |
| 07-09 | v2 | 点火确认 + MiniMax + PDF导出 |
| 07-09 | v3 | 两步诊断法 + 禁用概念不清 |
| 07-09 | v4 | 列比1.5:5:2 + 按钮两行对称 |
| 07-09 | v5 | 逐题格式强化 + 题号标注 |
| 07-09 | v6 | 安全审计P0修复 + 登录页重构 |
| 07-09 | v7 | CSS美化 + 动画效果 |
| 07-09 | v8 | 登录页重构：成绩目标移首行 + 手机号验证码独立行 |
| 07-09 | v9 | 个人信息页重排：手机验证行 + 框体统一12px |
| 07-09 | v10 | PDF下载用reportlab实现，无需额外安装 |
| 07-09 | v11 | 错题集支持周/月/学期三种时间跨度 |
| **07-18** | **v12** | **诊断V2.1（几何证明专项+corrective_guidance）+ MinerU OCR管道V2（支持PDF）+ 主力模型切DeepSeek + api_v2错误消息修复 + 注册验证码校验** |
| **08-04** | **v13** | **"还糊涂"标记（markErrorConfused：need_review+stage重置+糊涂优先排序）+ 已掌握清标记 + 四按钮面板 + 周末复盘糊涂优先** |
| **08-04** | **v14** | **BKT贝叶斯知识追踪正式落地（BKTTracker+3 API+诊断自动上报+错题变式自动闭环+掌握度进度条展示）** |
| **08-04** | **v15** | **学习页布局定稿：错因分析移右栏、老师悬浮卡片、去AI字眼、综合评价圆徽(优绿/良黄/差红)、三栏折叠、课前预习回左栏** |

## 安全审计
完整报告见 `references/security_audit.md`。P0修复（认证白名单 + 127.0.0.1绑定）已上线。
P1/P2项（旧API迁移、文件类型校验）列入后续迭代。

## 参考资料
- `references/ui_preferences.md` — UI布局偏好（邱董铁律）
- `references/security_audit.md` — 安全审计报告（2026-07-09）
- `references/implementation.md` — 实现参考与已知问题
- `references/layout_lessons.md` — 布局迭代教训
- `references/token_saving.md` — Token节省策略
- `references/llm_providers.md` — LLM提供商配置
- `references/diagnosis-prompt-format.md` — 错因诊断Prompt格式规范（两步法+题号强制+三级置信度）
- `references/diagnosis-format.md` — 诊断格式要求
- `references/fix-20260718.md` — 2026-07-18 诊断V2.1 + MinerU + 注册修复 + 模型切换
