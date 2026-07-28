#!/usr/bin/env python3
"""
邱数智方 · 张博士教研共同体 - 初中数学教学案例下载
==================================================
基于 Playwright + Sogou WeChat 搜索，下载公众号中初中数学教学案例。
保存为 Markdown 格式到 E:\《备课专业化》

使用方法：
    python download_zhang_math_cases.py

参数：
    --account  公众号名称（默认：张博士教科研共同体）
    --query    搜索关键词（默认：初中数学 教学设计）
    --output   保存目录（默认：E:\\《备课专业化》\\初中数学案例）
    --max      最多下载文章数（默认：20）
"""

import asyncio, urllib.parse, re, os, sys, argparse
from playwright.async_api import async_playwright, TimeoutError as PTimeout

DEFAULT_ACCOUNT = "张博士教科研共同体"
DEFAULT_QUERY = "初中数学 教学设计"
DEFAULT_OUTPUT = r"E:\《备课专业化》\初中数学案例"
MAX_ARTICLES = 20


async def search_articles(account, query, max_count):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        search_query = f"{account} {query}"
        search_url = ("https://weixin.sogou.com/weixin?type=2&query="
                     + urllib.parse.quote(search_query) + "&ie=utf8")

        print(f"[1/4] 搜索: {search_query}")
        await page.goto(search_url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 检查验证码
        content = await page.content()
        if "验证码" in content or "captcha" in content.lower():
            print("⚠️  触发验证码！尝试等待后重试...")
            await page.wait_for_timeout(8000)
            content = await page.content()
            if "验证码" in content:
                print("❌ 验证码无法自动绕过！")
                print(f"   请手动访问: {search_url}")
                await browser.close()
                return []

        # 提取文章列表
        articles = await page.evaluate("""
            () => {
                const items = document.querySelectorAll('.txt-box');
                return Array.from(items).map((item, i) => {
                    const titleEl = item.querySelector('h3 a');
                    const summaryEl = item.querySelector('.str_info');
                    const dateEl = item.querySelector('.s2');
                    return {
                        idx: i,
                        title: titleEl ? titleEl.textContent.trim() : '',
                        summary: summaryEl ? summaryEl.textContent.trim() : '',
                        date: dateEl ? dateEl.textContent.trim() : ''
                    };
                });
            }
        """)

        print(f"[2/4] 找到 {len(articles)} 篇文章")
        for a in articles[:max_count]:
            print(f"   [{a['idx']}] {a['date']} {a['title'][:60]}")

        # 下载每篇文章
        downloaded = []
        links = await page.query_selector_all('.txt-box h3 a')

        for i in range(min(len(links), max_count)):
            try:
                links = await page.query_selector_all('.txt-box h3 a')
                if i >= len(links):
                    break

                print(f"\n[3/4] 下载 [{i}]: {articles[i]['title'][:50]}...")

                async with context.expect_page(timeout=15000) as new_page_info:
                    await links[i].click()

                new_page = await new_page_info.value
                await new_page.wait_for_load_state("networkidle", timeout=15000)
                await new_page.wait_for_timeout(3000)

                # 滚动加载全文
                await new_page.evaluate("""
                    async () => {
                        const delay = ms => new Promise(r => setTimeout(r, ms));
                        for (let j = 0; j < 80; j++) {
                            window.scrollBy(0, 400);
                            await delay(200);
                        }
                    }
                """)
                await new_page.wait_for_timeout(3000)

                # 提取正文
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

                await new_page.close()

                downloaded.append({
                    "idx": i,
                    "title": pg_title or articles[i]['title'],
                    "date": articles[i]['date'],
                    "url": real_url,
                    "text": text
                })

                print(f"   ✅ {len(text)} 字符")

            except Exception as e:
                print(f"   ❌ 错误: {e}")
                continue

        await browser.close()
        return downloaded


def save_articles(articles, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    saved = []
    for a in articles:
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', a['title'])[:80]
        filename = f"{a['idx']:02d}_{safe_title}.md"
        filepath = os.path.join(output_dir, filename)

        md = f"""---
title: "{a['title']}"
source: "公众号·张博士教科研共同体"
url: "{a['url']}"
downloaded: "{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}"
category: "初中数学教学案例"
---

# {a['title']}

> **来源：** 公众号「张博士教科研共同体」
> **链接：** [{a['url']}]({a['url']})
> **下载时间：** {__import__('datetime').datetime.now().strftime('%Y年%m月%d日 %H:%M')}

---

{a['text']}

---

*本文由邱数智方·微信公众号下载工具自动采集，仅供教学研究使用。*
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)

        saved.append(filepath)
        print(f"   已保存: {os.path.basename(filepath)}")

    return saved


async def main():
    parser = argparse.ArgumentParser(description="张博士教研共同体-初中数学案例下载")
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--max", type=int, default=MAX_ARTICLES)
    args = parser.parse_args()

    print(f"""
╔═══════════════════════════════════════════╗
║   张博士教研共同体 · 初中数学案例下载工具   ║
╚═══════════════════════════════════════════╝
公众号: {args.account}
关键词: {args.query}
保存至: {args.output}
最多:   {args.max} 篇
""")

    articles = await search_articles(args.account, args.query, args.max)

    if not articles:
        print("\n❌ 未获取到任何文章")
        search_url = ("https://weixin.sogou.com/weixin?type=2&query="
                     + urllib.parse.quote(f"{args.account} {args.query}") + "&ie=utf8")
        print(f"   请手动访问: {search_url}")
        return

    files = save_articles(articles, args.output)

    print(f"\n{'='*50}")
    print(f"✅ 下载完成！共 {len(files)} 篇")
    print(f"📂 保存位置: {args.output}")
    print(f"{'='*50}")

    # 生成索引
    index_path = os.path.join(args.output, "README.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(f"# 初中数学教学案例索引\n\n")
        f.write(f"> 来源：公众号「{args.account}」\n")
        f.write(f"> 关键词：{args.query}\n")
        f.write(f"> 下载时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| 序号 | 标题 | 字数 |\n")
        f.write("|:----:|:-----|:----:|\n")
        for a in articles:
            title_short = a['title'][:60].replace('|', '\\|')
            f.write(f"| {a['idx']} | {title_short} | ~{len(a['text'])} |\n")

    print(f"📋 索引文件: {index_path}")


if __name__ == "__main__":
    asyncio.run(main())
