# api_v2 响应解包模式（2026-07-06 学霸基本法实战）

## 问题

FastAPI后端统一返回格式：`{code: 0, data: {...}, message: "ok"}`
前端直接读取 `data.text` 或 `data.analysis` 得到 `undefined`，因为实际数据在 `data.data` 下。

## 影响范围

学霸基本法重构中有3处受此bug影响：

| 端点 | 前端错误读取 | 正确解包 | 修复耗时 |
|:-----|:------------|:---------|:--------:|
| `/api/v2/ocr/recognize` | `data.text` | `data.data.text` | ~20分钟 |
| `/api/v2/diagnose/analyze` | `data.analysis` | `data.data.analysis` | ~15分钟 |
| `/api/v2/practice/generate` | `data.practice` | `data.data.practice` | ~10分钟 |

## 标准解包模式

```javascript
.then(function(data) {
  /* 解包api_v2格式 */
  var result = data;
  if (data.code !== undefined && data.data !== undefined) {
    result = data.data || {};
  }
  // 现在可以安全使用 result.text, result.analysis 等
})
```

## 通用工具函数

```javascript
function unwrapApiResponse(data) {
  if (data && data.code !== undefined && data.data !== undefined) {
    return data.data;
  }
  if (data && data.success !== undefined) {
    return data.data || data;
  }
  return data;
}
```

## 预防

每次新增API端点时，前端调用方必须做解包。两种格式共存时用属性判断区分：

- `api_v2`: `data.code !== undefined` → 取 `data.data`
- `api_v1`: `data.success !== undefined` → 取 `data.data || data`
