# 微信公众号文章下载技术笔记

> 适用场景：下载「张博士教科研共同体」等公众号文章
> 保存位置：`E:\《备课专业化》\`

## 方法一：Kimi WebBridge（推荐）

通过操控Chrome浏览器完成搜狗微信搜索→打开文章→提取内容全流程。

**安装前提：**
1. Chrome浏览器 + Kimi WebBridge扩展（CRX从chajianxw.com下载离线安装）
2. `kimi-webbridge start` 启动daemon（端口10086）
3. 验证 `kimi-webbridge status` → `extension_connected: true`

**API调用方式：**
```
POST http://127.0.0.1:10086/command
Body: {"action": "navigate|evaluate|close_tab", "args": {...}, "session": "任务名"}
```

**关键步骤：**
1. 搜狗微信搜索：`https://weixin.sogou.com/weixin?type=2&query={编码后的关键词}`
2. 获取文章列表：`evaluate` 执行JS提取 `.txt-box h3 a` 的href
3. 打开文章：`navigate` 到文章URL（newTab: true）
4. 滚动加载：多次 `window.scrollTo(0, document.body.scrollHeight)` 间隔1-2秒
5. 提取内容：`document.getElementById('js_content').innerText`
6. 下载图片：提取 `data-src` 属性中的 mmbiz.qpic.cn 链接
7. 关闭标签页：`close_tab`

**反爬对策：**
- 搜狗/微信在连续请求后会返回 ERR_CONNECTION_REFUSED
- 控制频率：每次操作间隔5秒以上，每批不超过5篇
- 触反爬后等待30分钟再试

## 方法二：Playwright（备用）

已有脚本：`beike-zhuanyehua/scripts/wechat-article-downloader.py`

## 保存格式

- 路径：`E:\《备课专业化》\初中数学案例\`
- 文件名：`序号_标题.md`
- 格式：YAML frontmatter + 正文

## 已知问题

- 教学设计内容通常以图片发布，文字提取不到完整表格
- 搜狗链接有时效性
