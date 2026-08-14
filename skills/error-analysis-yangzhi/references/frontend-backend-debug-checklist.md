# 前后端集成调试清单（2026-07-06 学霸基本法实战经验）

## 1. 上传/文件对话框不弹出

| 检查项 | 工具 | 说明 |
|:-------|:-----|:------|
| `<input type="file">` 是否存在 | F12 Elements | 搜索 `id="fi"` 确认元素存在 |
| 事件监听是否注册 | F12 Console → 点按钮看控制台 | 在click处理函数内加 `console.log()` |
| `capture` 属性 | 检查HTML | `capture="environment"` 在桌面Chrome上阻止文件对话框弹出 |
| `accept` 属性 | 检查HTML | `accept="image/*,.pdf"` 正常；但OCR不处理PDF |
| 浏览器缓存 | Ctrl+Shift+R强制刷新 | 304 Not Modified表示浏览器用缓存旧版本 |
| 换浏览器 | Chrome/Firefox/Edge交叉验证 | 排除特定浏览器bug |
| 服务是否正常 | `curl http://127.0.0.1:8000/api/health` | 返回 `{"status":"ok"}` 正常 |

## 2. API返回404/422

| 现象 | 根因 | 修复 |
|:-----|:------|:------|
| 前端调 `/api/v2/ocr` 后端只有 `/api/v2/ocr/recognize` | 路径不匹配 | `grep -r "fetch(" static/` 比对 `grep -r "@router" routers/` |
| POST请求422 | 请求体格式不匹配 | 前端发JSON base64，后端要UploadFile → 后端改接受Request自动判断格式 |
| GET返回405 | curl用HEAD请求 | 改用 `curl -s http://...` (GET) |
| 连续404无报错 | 前端静默失败 | 加 `.catch(function(err){console.log(err)})` |

## 3. API返回200但前端不显示

| 现象 | 根因 | 修复 |
|:-----|:------|:------|
| OCR返回text但显示"未识别到文字" | api_v2响应未解包 | `data.code !== undefined → data = data.data` |
| 诊断返回analysis但面板空白 | 同上 | 同上 |
| OCR返回boxes但不显示叠加框 | 同上 | 同上 |

## 4. DeepSeek API调用失败

| 错误 | 原因 | 修复 |
|:-----|:------|:------|
| `ImportError: from_json from jiter` | openai库与jiter版本冲突 | `pip install --ignore-installed jiter==0.15.0` |
| `DEEPSEEK_API_KEY 未配置` | env变量未加载 | `export DEEPSEEK_API_KEY=$(grep ^DEEPSEEK_API_KEY= server/.env \| cut -d= -f2)` |
| `AuthenticationError: API key format incorrect` | Key格式不对 | 检查key是否来自正确平台（火山方舟vs DeepSeek） |

## 5. OCR引擎问题

| 错误 | 原因 | 修复 |
|:-----|:------|:------|
| `ValueError: Unknown argument: show_log` | PaddleOCR版本升级参数变了 | 改用RapidOCR |
| `NotImplementedError: ConvertPirAttribute...` | PaddlePaddle版本冲突 | 换RapidOCR |
| OCR耗时25秒+ | 首次加载模型 | 后续调用会快（~7秒） |

## 6. 调试流程（推荐）

```
① 确认服务运行: curl /api/health
② 测试API直接调: python/curl发请求检查返回
③ 检查服务器日志: 看POST请求是否到达
④ 浏览器F12 Console: 看JS错误和console.log
⑤ 强制刷新: Ctrl+Shift+R
⑥ 换浏览器验证
```
