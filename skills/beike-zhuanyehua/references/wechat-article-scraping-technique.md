# WeChat公众号文章爬取技术方案

## 背景
在中国大陆网络环境下，搜狗微信搜索（weixin.sogou.com）是唯一可公开检索微信公众号文章的平台，但存在以下障碍：
1. 搜狗搜索有反爬机制（人机验证码）
2. 文章URL需要JavaScript动态重定向（搜狗→mp.weixin.qq.com）
3. 公众号文章内容常以图片形式呈现（需滚动触发懒加载）
4. 百度/Bing不收录公众号文章

## 技术方案：Playwright无头浏览器

### 环境要求
```bash
pip install playwright
playwright install chromium  # 首次使用需要
```

### 核心流程
```
① 搜狗搜索 → ② 获取文章列表 → ③ 点击文章链接（JS重定向）→ ④ 等待mp.weixin.qq.com加载 → ⑤ 滚动触发图片懒加载 → ⑥ 提取文本+图片URL
```

### 关键代码

#### 1. 搜狗搜索文章
```python
import urllib.parse
search_url = "https://weixin.sogou.com/weixin?type=2&query=" + urllib.parse.quote("公众号名 关键词") + "&ie=utf8"
# type=2 表示搜文章，type=1 表示搜公众号
```

#### 2. Playwright点击链接+跟随重定向
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    page = await context.new_page()
    await page.goto(search_url, timeout=20000, wait_until="networkidle")
    
    # 点击第一条文章链接，使用expect_page捕获新页面
    links = await page.query_selector_all('.txt-box h3 a')
    async with context.expect_page(timeout=15000) as new_page_info:
        await links[0].click()
    
    article_page = await new_page_info.value
    await article_page.wait_for_load_state("networkidle")
    real_url = article_page.url
    # real_url 即为 mp.weixin.qq.com 的真实文章URL
```

#### 3. 滚动触发懒加载
```python
await article_page.evaluate("""
    async () => {
        const delay = ms => new Promise(r => setTimeout(r, ms));
        for (let i = 0; i < 60; i++) {
            window.scrollBy(0, 400);
            await delay(200);
        }
    }
""")
await article_page.wait_for_timeout(3000)
```

#### 4. 提取文章内容
```python
# 提取文本
text = await article_page.evaluate("""
    () => {
        const content = document.querySelector('#js_content');
        return content ? content.innerText : document.body.innerText;
    }
""")

# 提取图片URL
img_urls = await article_page.evaluate("""
    () => {
        const imgs = document.querySelectorAll('#js_content img');
        return Array.from(imgs).map(img => ({
            src: img.getAttribute('data-src') || img.getAttribute('src') || '',
            alt: img.getAttribute('alt') || ''
        }));
    }
""")
```

### 常见问题

| 问题 | 原因 | 解决 |
|:----|:-----|:------|
| 搜狗返回验证码页面 | 反爬机制触发 | 用Playwright启动完整Chromium（非requests） |
| 文章内容只有几百字符 | 内容以图片形式呈现 | 接受图片形式，保存图片URL后额外OCR |
| 文章URL被重定向到搜狗首页 | session过期 | 重新从搜狗搜索开始，使用同一browser context |
| 连接超时 | 网络波动 | 增加timeout，或用网线/代理切换网络 |

### 保存格式
推荐保存为Markdown格式：
```markdown
# 文章标题
> **原文链接：** {real_url}
> **下载时间：** {date}
> **来源：** 公众号"xxx"

---

{full_text}
```

### 完善后的项目脚本路径
`C:\Users\HUAWEI\AppData\Local\hermes\skills\company-skills\beike-zhuanyehua\scripts\wechat-article-downloader.py`
