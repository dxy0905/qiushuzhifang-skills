# 学霸基本法 OCR 多后端配置

## 架构

```
拍照/上传 → ocr_with_backend("auto")
  ├─ 1️⃣ Mistral OCR (需MISTRAL_API_KEY)
  ├─ 2️⃣ Baidu Unlimited-OCR (已配置 ✅)  
  ├─ 3️⃣ MinerU (本地, 保底 ✅)
  └─ 4️⃣ RapidOCR (本地, 极速 ✅)
```

## 后端代码位置

```
/opt/xueba/server/services/
├── ocr_pipeline.py          # 主管道 - 已集成 ocr_with_backend()
├── ocr_backends/
│   ├── mistral_ocr.py       # Mistral OCR 客户端
│   └── unlimited_ocr.py     # 百度 Unlimited-OCR 客户端
```

## 配置

### 百度OCR（已激活·AppID: 7922689）

```bash
# /opt/xueba/server/.env
BAIDU_OCR_API_KEY=PZFLxJP68Hojy7zOzbhSBmcS
BAIDU_OCR_SECRET_KEY=osLeBK7Z9KtWgkyNQo1GAgDmV3JgGgCu
```

### Mistral OCR（被墙，需VPN）

```bash
echo "MISTRAL_API_KEY=***" >> /opt/xueba/server/.env
```

## 百度OCR API要点

1. token获取：`POST https://aip.baidubce.com/oauth/2.0/token` → `grant_type=client_credentials`
2. OCR调用：`POST https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic`
3. 图片传base64编码，`Content-Type: application/x-www-form-urlencoded`
4. Unicode编码问题：Python f-string中的`\uXXXX`在heredoc中会报错，用`+`拼接
5. 首次调用无返回结果 → 检查PIL字体（服务器无中文字体导致空白图片）

## 使用

```python
from ocr_pipeline import ocr_with_backend
result = ocr_with_backend("photo.png", backend="auto")  # 自动路由
```
