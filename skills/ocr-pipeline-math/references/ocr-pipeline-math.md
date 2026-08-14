# 数学作业OCR增强管道详细参考

## 完整处理流程

```
学生上传作业图片 (JPEG/PNG, ≤20MB)
    ↓
1. 预处理 — 降采样（长边≤2000px）
    ↓
2. 版面分析 — MinerU OCR → 按题号拆分
    ↓
3. 公式识别 — LaTeX-OCR → 数学公式→LaTeX代码
    ↓
4. 符号修正 — _fix_math_symbols() → √±≠≤≥×²³
    ↓
5. 错因诊断 — DeepSeek CLTA 5分类法
    ↓
6. 综合评价 — 正确/错误统计 + 等级评定
```

## 核心API

`POST /api/v2/ocr/enhanced`
- 输入: `multipart/form-data` 图片文件
- 输出: `{ocr_text, problems: [{number, error_types, analysis}], evaluation: {total, correct, error_distribution, grade}}`

## 数学符号修正规则

| OCR误识 | 修正 | 场景 |
|:--------|:-----|:------|
| V / J | √ | 根号 |
| 士 | ± | 正负号 |
| != / ! = | ≠ | 不等号 |
| <= / < = | ≤ | 小于等于 |
| >= / > = | ≥ | 大于等于 |
| 数字间x/X | × | 乘号 |
| >Q.X7 | √ | 已知乱码案例 |
| digit^2 | digit² | 上标平方 |

## 综合评价等级

- 优秀: ≥90%
- 良好: ≥75%
- 及格: ≥60%
- 需努力: <60%
