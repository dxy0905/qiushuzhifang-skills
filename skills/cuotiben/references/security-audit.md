# 安全审计参考（2026-07-09）

适用于学霸基本法及同类FastAPI+SQLite项目。

## 快速检查清单

```bash
# 1. 端口绑定
netstat -ano | findstr "8001"  # 确认127.0.0.1，非0.0.0.0

# 2. 认证白名单
grep "exclude_paths" server/middleware/auth_middleware.py

# 3. 敏感路径
grep "db_path\|api_key\|secret" --include="*.py" -r .

# 4. CORS配置
grep "allow_origins" server/main.py

# 5. 日志泄漏
grep "request.body\|body=\|request_body" --include="*.py" -r .
```

## P0必修复项

| 项 | 标准 | 检查命令 |
|:---|:------|:---------|
| 服务监听 | `127.0.0.1` 仅本地 | `netstat -ano \| findstr :8001` |
| 删除操作需认证 | 白名单不含 `/delete` | `grep delete middleware/*.py` |
| 不返回db路径 | health接口不暴露路径 | curl `/api/health` |
| API Key不在日志 | 日志不记录请求体 | `grep body logger\|print` |
