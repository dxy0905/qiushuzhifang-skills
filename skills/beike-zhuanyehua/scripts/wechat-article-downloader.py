#!/usr/bin/env python3
"""
邱数智方 · 微信公众号文章下载工具
=====================================
基于 Playwright + Sogou WeChat 搜索，下载指定公众号的文章。

用途：每月下载"张博士教科研共同体"公众号的新推送文章。
适用：教育部全员（严教牵头，张训技术支持）

使用方法：
    python wechat-article-downloader.py --account "张博士教科研共同体" --query "学教评一致性"
    
参数：
    --account  公众号名称（默认：张博士教科研共同体）
    --query    搜索关键词（默认：学教评一致性）
    --output   保存目录（默认：E:\\《备课专业化》\\）
    --max      最多下载文章数（默认：10）

依赖安装：
    pip install playwright
    playwright install chromium
"""

import asyncio, urllib.parse, re, os, sys, argparse
from playwright.async_api import async_playwright, TimeoutError as PTimeout

# ============== 配置 ==============
DEFAULT_ACCOUNT = "张博士教科研共同体"
DEFAULT_QUERY = "学教评一致性"
DEFAULT_OUTPUT = r"E:\《备课专业化》"
MAX_ARTICLES = 10
SEARCH_TIMEOUT = 20000
CLICK_TIMEOUT = 15000
SCROLL_STEPS = 60
SCROLL_DELAY = 200

# ============== 核心逻辑 ==============

async def search_articles(account, query, max_count):
    """通过搜狗微信搜索获取文章列表"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # 1. 构造搜狗微信搜索URL
        search_query = f"{account} {query}"
        search_url = ("https://weixin.sogou.com/weixin?type=2&query=" 
                     + urllib.parse.quote(search_query) + "&ie=utf8")
        
        print(f"[1/4] 搜索: {search_query}")
        await page.goto(search_url, timeout=SEARCH_TIMEOUT, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # 检查验证码
        content = await page.content()
        if "验证码" in content or "captcha" in content.lower():
            print("⚠️  触发验证码！尝试等待后重试...")
            await page.wait_for_timeout(5000)
            content = await page.content()
            if "验证码" in content:
                print("❌ 验证码无法自动绕过，请手动在浏览器中访问：")
                print(f"   {search_url}")
                await browser.close()
                return []
        
        # 2. 提取文章列表
        articles = await page.evaluate("""
            () => {
                const items = document.querySelectorAll('.txt-box');
                return Array.from(items).map((item, i) => {
                    const titleEl = item.querySelector('h3 a');
                    const summaryEl = item.querySelector('.str_info');
                    return {
                        idx: i,
                        title: titleEl ? titleEl.textContent.trim() : '',
                        summary: summaryEl ? summaryEl.textContent.trim() : ''
                    };
                });
            }
        """)
        
        print(f"[2/4] 找到 {len(articles)} 篇文章（将下载前 {min(max_count, len(articles))} 篇）")
        for a in articles[:max_count]:
            print(f"   [{a['idx']}] {a['title'][:60]}")
        
        # 3. 获取每篇文章的链接并下载
        downloaded = []
        links = await page.query_selector_all('.txt-box h3 a')
        
        for i in range(min(len(links), max_count)):
            try:
                # Re-query links each iteration (page may change)
                links = await page.query_selector_all('.txt-box h3 a')
                if i >= len(links):
                    break
                
                print(f"\n[3/4] 下载 [{i}]: {articles[i]['title'][:50]}...")
                
                # 点击链接，跟随重定向
                async with context.expect_page(timeout=CLICK_TIMEOUT) as new_page_info:
                    await links[i].click()
                
                new_page = await new_page_info.value
                await new_page.wait_for_load_state("networkidle", timeout=CLICK_TIMEOUT)
                await new_page.wait_for_timeout(3000)
                
                # 滚动触发懒加载
                await new_page.evaluate("""
                    async () => {
                        const delay = ms => new Promise(r => setTimeout(r, ms));
                        for (let j = 0; j < """ + str(SCROLL_STEPS) + """; j++) {
                            window.scrollBy(0, 400);
                            await delay(""" + str(SCROLL_DELAY) + """);
                        }
                    }
                """)
                await new_page.wait_for_timeout(3000)
                
                # 提取内容
                text = await new_page.evaluate("""
                    () => {
                        const jsc = document.querySelector('#js_content');
                        if (!jsc) return document.body.innerText || '';
                        jsc.style.maxHeight = 'none';
                        jsc.style.overflow = 'visible';
                        return jsc.innerText || '';
                    }
                """)
                
                pg_title = await new_page.title()
                real_url = new_page.url
                
                # 提取图片
                img_urls = await new_page.evaluate("""
                    () => {
                        const imgs = document.querySelectorAll('#js_content img');
                        return Array.from(imgs).slice(0, 5).map(img => ({
                            src: img.getAttribute('data-src') || img.getAttribute('src') || '',
                            alt: img.getAttribute('alt') || ''
                        }));
                    }
                """)
                
                await new_page.close()
                
                downloaded.append({
                    "idx": i,
                    "title": pg_title or articles[i]['title'],
                    "url": real_url,
                    "text": text,
                    "images": img_urls
                })
                
                chars = len(text)
                print(f"   ✅ {chars} 字符")
                
            except Exception as e:
                print(f"   ❌ 错误: {e}")
                continue
        
        await browser.close()
        return downloaded


def save_articles(articles, output_dir, prefix=""):
    """保存文章到本地"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    saved = []
    for a in articles:
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', a['title'])[:80]
        filename = f"{prefix}{a['idx']:02d}_{safe_title}.md"
        filepath = os.path.join(output_dir, filename)
        
        md = f"""# {a['title']}

> **原文链接：** {a['url']}
> **下载工具：** 邱数智方·微信公众号文章下载工具
> **下载时间：** {__import__('datetime').datetime.now().strftime('%Y年%m月%d日 %H:%M')}
> **来源：** 公众号"张博士教科研共同体"

---

{a['text']}

"""
        if a['images']:
            md += "\n---\n**文章中包含的图片：**\n"
            for img in a['images']:
                md += f"- {img['alt'] or '图片'}: {img['src']}\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
        
        saved.append(filepath)
        print(f"   已保存: {filepath}")
    
    return saved


async def main():
    parser = argparse.ArgumentParser(description="微信公众号文章下载工具")
    parser.add_argument("--account", default=DEFAULT_ACCOUNT, help="公众号名称")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="搜索关键词")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="保存目录")
    parser.add_argument("--max", type=int, default=MAX_ARTICLES, help="最多下载篇数")
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════╗
║   邱数智方 · 微信公众号文章下载工具   ║
╚══════════════════════════════════════╝
公众号: {args.account}
关键词: {args.query}
保存至: {args.output}
最多:   {args.max} 篇
    """)
    
    articles = await search_articles(args.account, args.query, args.max)
    
    if not articles:
        print("\n❌ 未获取到任何文章")
        print("可能原因：")
        print("1. 搜狗微信搜索需要手动验证 — 请在浏览器中打开以下链接手动搜索：")
        search_url = ("https://weixin.sogou.com/weixin?type=2&query=" 
                     + urllib.parse.quote(f"{args.account} {args.query}") + "&ie=utf8")
        print(f"   {search_url}")
        print("2. 公众号名称不准确")
        print("3. 网络连接问题")
        return
    
    files = save_articles(articles, args.output)
    
    print(f"\n{'='*50}")
    print(f"✅ 下载完成！共 {len(files)} 篇")
    print(f"📂 保存位置: {args.output}")
    print(f"{'='*50}")
    
    # 生成目录索引
    index_path = os.path.join(args.output, "公众号文章索引.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(f"# 公众号文章索引\n\n")
        f.write(f"> 来源：{args.account}\n")
        f.write(f"> 关键词：{args.query}\n")
        f.write(f"> 下载时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| 序号 | 标题 | 字数 |\n")
        f.write("|:----:|:-----|:----:|\n")
        for a in articles:
            f.write(f"| {a['idx']} | {a['title'][:60]} | ~{len(a['text'])} |\n")
    
    print(f"📋 索引文件: {index_path}")


if __name__ == "__main__":
    asyncio.run(main())
