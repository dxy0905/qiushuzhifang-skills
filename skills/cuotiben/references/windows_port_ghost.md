# Windows端口管理 · 幽灵进程处理

## 问题

8000端口被PID 5496占用，所有kill命令无效（taskkill/Stop-Process/Python os.kill）。

## 根因

该进程是Docker Desktop的WSL网络代理进程，在Windows进程列表中不可见（`Get-Process`找不到），但TCP端口仍被绑定。

## 验证

```bash
netstat -ano | grep ":8000" | grep LISTENING
# → TCP 0.0.0.0:8000  LISTENING  5496
tasklist /FI "PID eq 5496"
# → 找不到该进程（进程已死但端口未释放）
```

## 解决方案

| 方案 | 效果 | 副作用 |
|:-----|:------|:--------|
| `wsl --shutdown` | 有时释放 | 关闭所有WSL容器 |
| 重启Docker Desktop | 可能释放 | 需等待Docker重启 |
| **修改服务端口**（推荐） | 立即可用 | 修改main.py/start_server.py中的port参数 |
| 重启电脑 | 100%释放 | 需中断工作 |

## 当前端口配置（2026-07-20 确认）

`start_server.py`（重构版入口）使用 **8000端口**：
```python
uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=False)
```

⚠️ 历史遗留：此前曾改用8080端口（旧重构版），但最新版 `start_server.py` 已回退至8000。如果8080无响应，优先检查8000端口。不要同时运行两个实例——`start_server.py` 内置单实例锁（`.server_pid`文件），但两次不同端口的启动不受此锁保护。

## 端口健康检查

```bash
# 快速检查服务是否运行
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health --connect-timeout 3
# 返回 200 → 服务运行中
# 返回 000 → 服务未运行，需启动

# 启动服务（background模式）
cd /d/邱数智方/项目/学霸基本法 && python start_server.py
# 等待3-5秒再检查
```

## 最佳实践

- 学霸基本法服务器运行在 **8000端口**
- 用户访问 `http://127.0.0.1:8000` 进入前端
- API文档在 `http://127.0.0.1:8000/docs`
- 服务器只监听本地，安全性一致
