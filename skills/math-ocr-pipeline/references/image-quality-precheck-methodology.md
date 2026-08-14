# 图片质量预检方法（check_image_quality）

## 位置
`OCREngine.check_image_quality(image_path)` in `agent_service.py`

## 检测项

| 检测 | 方法 | 阈值 | 说明 |
|------|------|------|------|
| 模糊度 | Laplacian 方差 | <100 = 模糊 | 3×3 Laplacian 核 `[[0,1,0],[1,-4,1],[0,1,0]]` |
| 亮度 | 灰度均值 | <30 过暗, >220 过曝 | 0-255范围 |
| 对比度 | 灰度标准差 | <20 对比度不足 | 低对比度图片OCR识别率差 |
| 尺寸 | 宽高最小值 | <50px reject | 图片太小无法OCR |

## 综合评分公式

```python
score = min(100, 
    lap_var/200*40 +          # 模糊度权重40%
    (1-abs(mean-128)/128)*30  # 亮度权重30%
    + min(std/50,1)*30)       # 对比度权重30%
```

## 三级决策

| 分数 | 决策 | 含义 |
|:----:|:----:|:------|
| ≥50 | continue | 质量可接受，正常处理 |
| 20-49 | warn | 质量偏低，OCR可能不准 |
| <20 | reject | 太差，提示用户重拍 |

## 降级路径
- `ImportError`（无 numpy/scipy）或文件不存在 → 自动返回 `continue`，不阻断主流程
- 异常 → `logger.warning` 记录后返回 `continue`

## 实测效果
- 模糊照片（手抖）：Laplacian≈20-50 → warn
- 正常手机拍照：Laplacian≈200-500 → continue
- 过暗（台灯未开）：亮度≈15-25 → warn
- 过曝（闪光灯太近）：亮度≈230-250 → warn
