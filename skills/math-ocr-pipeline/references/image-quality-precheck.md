# 图片质量预检方法（check_image_quality）

## 原理

OCR前先检测图片质量，避免低质量图片浪费token和导致诊断错误。

## 三维检测

| 维度 | 方法 | 阈值 | 说明 |
|------|------|------|------|
| **模糊度** | Laplacian 方差（卷积核[[0,1,0],[1,-4,1],[0,1,0]]） | <100=模糊 | 方差越小越模糊（全黑图片方差≈0） |
| **亮度** | 灰度均值（0-255） | <30过暗, >220过曝 | 拍照环境光线不足或过强 |
| **对比度** | 灰度标准差 | <20低对比度 | 文字和背景区分不明显 |

## 综合评分

```python
score = (
    lap_var/200 * 40           # 模糊度权重40%
    + (1 - abs(mean-128)/128) * 30  # 亮度权重30%
    + min(std/50, 1) * 30      # 对比度权重30%
)
score = int(min(100, score))
```

## 三级决策

| 区间 | 决策 | 前端行为 |
|------|------|---------|
| score >= 50 | continue | 正常OCR处理 |
| 20 <= score < 50 | warn | 显示警告但仍继续 |
| score < 20 | reject | 提示用户重拍 |

## 降级策略

当缺少依赖（numpy/scipy）或文件不存在时，静默返回 continue，不阻断流程。

## 调用时机

在 `OCREngine.recognize()` 方法最前面调用，放在降采样预处理之前：

```python
def recognize(self, image_path):
    qc = self.check_image_quality(image_path)
    if qc["decision"] == "reject":
        return {"text": "", "boxes": [], "confidence": 0.0,
                "quality_warning": qc["issues"], "decision": "reject"}
    # ... 继续降采样 + OCR ...
```
