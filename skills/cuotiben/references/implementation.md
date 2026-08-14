# 错题本 · 实现参考（2026-07-08会话）

## API实现

```python
# agent_routes.py — POST /api/v2/review/generate
# 核心逻辑：
# 1. 按period(week/month/semester)计算时间范围
# 2. 从知识库(kb_search)查询错题
# 3. 按时间过滤（datetime.strptime解析created_at字符串）
# 4. 按frequency/hit_count降序排列
# 5. 取前limit条（默认20，最大50）
# 6. 统计type_stats错因分布
# 7. 调用_render_review_html生成可打印HTML
```

## Cronjob定时推送

```bash
# 每周推送（周一09:00）
hermes cron create --schedule "0 9 * * 1" \
  --skill company-skills/board-secretary-tools \
  --name "错题集 · 每周推送" \
  --prompt "调用API POST /api/v2/review/generate ..."

# 月度推送（每月1日09:00）
hermes cron create --schedule "0 9 1 * *" \
  --skill company-skills/board-secretary-tools \
  --name "错题集 · 月度推送" \
  --prompt "调用API POST /api/v2/review/generate ..."
```

## 前端错题集按钮

```javascript
// index.html — 左栏底部加按钮
<span class="ub" id="bReview" style="background:#27ae60;color:#fff">[错题集]</span>

// app.js — 弹窗 → 选时间 → 调用API → 下载/打印
function openReviewDialog() { ... }
```

## 已知问题

| 问题 | 原因 | 修复 |
|:-----|:------|:------|
| `created_at`是字符串str | 知识库存的是datetime格式化字符串 | `datetime.strptime(c, '%Y-%m-%d %H:%M:%S')`解析后再比较 |
| `Cannot set properties of null (setting 'disabled')` | 确认按钮被移除后JS仍尝试操作 | 加`if (btn) { ... }`空判断 |
| 端口8000幽灵进程 | Docker/WSL占端口杀不掉 | 改用端口8001，或重启电脑 |
