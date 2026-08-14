# 多文件管理 + 每份独立OCR/诊断存储模式

## 适用场景
学习页支持学员上传多份练习材料，每份独立存储OCR识别结果和错因诊断结果，点击左侧文件列表可切换显示对应分析。

## 核心数据结构
```javascript
{
  name: "学生作业1.jpg",
  dataUrl: "data:image/jpeg;base64,...",
  uploaded: Date.now(),
  ocrData: { text: "...", boxes: [...], confidence: 0.9 },
  diagnosis: { analysis: "...", error_types: [...], suggestions: [...] },
  step: 3
}
```

## 三处必须同步存储
| 位置 | 内容 | 操作 |
|:-----|:-----|:-----|
| uploadFile() | 初始化ocrData/diagnosis/step | 新建文件时加字段 |
| performOcr() | cur.ocrData = ocrResult; cur.step = 2 | OCR完成后写入 |
| performDiagnosis() | cur.diagnosis = diag; cur.step = 3 | 诊断完成后写入 |

每次修改后必须 localStorage.setItem()

## selectFile切换
1. showImage(f.dataUrl) — 切图片
2. clearOcrBoxes() + showOcrBoxes(f.ocrData.boxes) — 恢复OCR框
3. showDiagnosis(f.diagnosis) — 恢复诊断

## 约束
- fileList存localStorage，刷新不丢
- currentFileIndex跟踪当前选中文件
