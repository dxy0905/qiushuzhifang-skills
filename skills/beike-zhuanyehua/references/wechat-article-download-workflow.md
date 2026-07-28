# 微信公众号文章下载 · 初中数学教学案例

## 来源
公众号「张博士教科研共同体」→ 作者：张爱军博士（备课专业化理念首倡者）

## 下载脚本
`scripts/download_zhang_math_cases.py` 基于 Playwright + 搜狗微信搜索

## 运行方式
```bash
cd scripts/
python download_zhang_math_cases.py --account "张博士教科研共同体" --query "初中数学 教学设计" --max 15
```

## 输出位置
`E:\《备课专业化》\初中数学案例\`

## 索引文件
每次运行自动生成 `E:\《备课专业化》\初中数学案例\README.md`

## 依赖
```bash
pip install playwright
playwright install chromium
```

## 技术原理
1. 搜狗微信搜索（weixin.sogou.com）→ type=2（文章搜索）
2. Playwright Chromium 无头浏览器模拟搜索
3. 提取文章列表（标题+日期+摘要）
4. 逐个点击进入文章详情页
5. 滚动触发公众号的懒加载
6. 提取 `#js_content` 中的正文内容
7. 保存为 YAML-frontmatter Markdown 文件

## 注意事项
- 搜狗搜索可能触发验证码（概率较低）
- 触发验证码时需手动访问搜索URL完成验证
- 公众号文章需滚动才能加载全文（脚本已自动滚动80次）
- 图片链接提取自 `data-src` 属性（懒加载）
