# LaTeX_OCR_PRO vs pix2tex 对比（2026-07-12）

## 背景
GitHub 搜索 `LaTeX_OCR_PRO`（LinXueyuanStdio, ⭐1,304）后发现名称含"PRO"，疑似增强版，但实际是旧版。

## 核心结论
**LaTeX_OCR_PRO 是旧版，学霸基本法已在用新版。不要安装。**

## 对比表

| 维度 | LaTeX_OCR_PRO | 学霸基本法当前使用(pix2tex) |
|------|---------------|---------------------------|
| 框架 | TensorFlow 1.12(2018) | PyTorch(现代) |
| Python | 3.5 仅 | 3.12 ✅ |
| 架构 | Seq2Seq+Attention+Beam Search | Transformer |
| 中文支持 | ❌ 无 | ✅ RapidOCR双引擎 |
| 符号纠错 | ❌ 无 | ✅ _fix_math_symbols 三层架构 |
| 图片质检 | ❌ 无 | ✅ check_image_quality 三级检测 |
| 安装难度 | TF1.12 环境冲突 | pip install pix2tex |
| 评分 | BLEU-4 90.47%, EditDist 93.36 | 现代模型更优 |

## 经验教训
- GitHub 上名称带"PRO"的项目不一定是增强版，可能是旧版TensorFlow项目
- 搜索到的开源项目应先检查依赖（TF1.12 vs PyTorch）再决定是否安装
- pix2tex（lukas-blecher）是 LaTeX_OCR_PRO 的 PyTorch 重写版，同源但架构完全不同
