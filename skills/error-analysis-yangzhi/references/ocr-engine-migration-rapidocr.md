# OCR引擎迁移记录（PaddleOCR → RapidOCR）

## 背景

学霸基本法项目OCR引擎从PaddleOCR迁移到RapidOCR。

## 问题

PaddleOCR v6 + PaddlePaddle版本冲突导致 `NotImplementedError`：
```
NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute not support 
[pir::ArrayAttribute<pir::DoubleAttribute>]  
(at ..\\paddle\\fluid\\framework\\new_executor\\instruction\\onednn\\onednn_instruction.cc:118)
```

## 解决方案

改用 `rapidocr-onnxruntime`（7k⭐）

```python
# 安装
pip install rapidocr-onnxruntime

# 使用
from rapidocr_onnxruntime import RapidOCR
engine = RapidOCR()
result, elapse = engine(image_path)
# result格式: [[box_coords, text, confidence], ...]
# box_coords: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
```

## 代码修改要点

1. 驱动类替换：`PaddleOCR` → `RapidOCR`
2. 调用方法替换：`ocr.ocr(path)` → `engine(path)`（返回tuple: (results, elapse)）
3. 返回格式解析：
   - PaddleOCR: `result[0][i][1][0]` = text, `result[0][i][1][1]` = confidence
   - RapidOCR: `result[i][1]` = text, `result[i][2]` = confidence
4. 参数简化：RapidOCR不需要 `lang`, `use_angle_cls` 等参数

## 与旧版app.py的兼容

学霸基本法旧版 `server.app:app` 用的PaddleOCR，新版 `server.main:app` 改用RapidOCR。start_server.py 已改为指向新模块。
