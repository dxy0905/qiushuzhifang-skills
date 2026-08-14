# 数学OCR纠错参考

## 函数位置

`D:\邱数智方\项目\学霸基本法\server\services\agent_service.py` → `OCREngine._fix_math_symbols()`

## 完整正则表

```python
import re

def fix_math_symbols(text: str) -> str:
    """OCR后数学符号上下文智能纠错"""
    
    # === 基础符号替换（有序，精确）===
    replacements = [
        ("V", "\u221a"), ("J", "\u221a"),               # 根号OCR误识
        ("\u58eb", "\u00b1"),                            # 正负号
        ("!=", "\u2260"), ("! =", "\u2260"),            # 不等号
        ("<=", "\u2264"), ("< =", "\u2264"),            # 小于等于
        (">=", "\u2265"), ("> =", "\u2265"),            # 大于等于
        (">Q.X7", "\u221a"), ("VX", "\u221a"), ("JX", "\u221a"),  # 乱码
        (")\u221a", ") \u221a"), (")×", ") ×"),         # 选项空格
    ]
    for old, new in replacements:
        if old != new:
            text = text.replace(old, new)
    
    # === 正则修复 ===
    
    # 数字乘号：5x3 → 5×3
    text = re.sub(r'(\d)\s*[xX]\s*(\d)', r'\1\u00d7\2', text)
    
    # 上标：仅字母后跟2/3（不匹配多位数中的2）
    text = re.sub(r'([a-z])\s*\^\s*2\b', r'\1\u00b2', text)
    text = re.sub(r'([a-z])\s*\^\s*3\b', r'\1\u00b3', text)
    text = re.sub(r'([a-z])2\b', r'\1\u00b2', text)  # x2 → x²
    
    # 变量x被识别为1（上下文感知）
    text = re.sub(r'(?<![.\d])(1)(?=[\u2264\u2265<>=](?:\s*\d|\s*x|\s*\u221a|\s*[a-z]))', 'x', text)
    text = re.sub(r'(\u53d6\u503c\u8303\u56f4\u662f)\s*1\s*([\u2264\u2265])', r'\1x\2', text)
    text = re.sub(r'(?:^|(?<=[\uff0c\u3002\uff1b\n]))\s*1\s*(?=[\u2264\u2265<>=])', 'x', text)
    
    # 根号括号补全：√x+4 → √(x+4)
    text = re.sub(r'\u221a([a-z])\s*([\u2264\u2265<>=+\-\u00d7\u00f7])\s*(\d)', r'\u221a(\1\2\3)', text)
    text = re.sub(r'\u221a(\d+)\s*([+\-])\s*(\d)', r'\u221a(\1\2\3)', text)
    
    # 选项空格：A.√7 → A. √7
    text = re.sub(r'([A-Za-z])\.([\u221a\u00d7\u00b1])', r'\1. \2', text)
    text = re.sub(r'([A-Za-z])\.(\d)', r'\1. \2', text)
    
    return text
```

## 测试用例

```python
test_cases = [
    ("1\u22643", "x\u22643"),           # x≤3
    ("x<=\u22643", "x\u22643"),          # x≤3（<=已转≤）
    ("1>=\u22655", "x\u22655"),          # x≥5
    ("\u53d6\u503c\u8303\u56f4\u662f1\u22643", "\u53d6\u503c\u8303\u56f4\u662fx\u22643"),
    ("\u221ax+4", "\u221a(x+4)"),        # √(x+4)
    ("A.\u221a7", "A. \u221a7"),          # A. √7
    ("12", "12"),                         # 不误改多位数
    ("x^2=25", "x\u00b2=25"),            # x²
    ("x=1", "x=1"),                       # 数字1合法
    ("3+4=7", "3+4=7"),                   # 正常算术
]
```
