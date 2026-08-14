# 作业设计Word文档生成指南（python-docx）

> 省赛要求提交.doc/.docx格式，纯文本md不符合提交要求。本指南提供从markdown到Word文档的自动化转换工作流。

---

## 一、安装

```bash
pip install python-docx
```

## 二、核心代码结构

```python
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

doc = Document()
style = doc.styles['Normal']
font = style.font
font.name = '微软雅黑'
font.size = Pt(11)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
```

## 三、关键函数

### 3.1 表头着色

```python
def set_cell_shading(cell, color):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)
```

### 3.2 表格创建（带交替行颜色）

```python
def add_table(doc, data):
    rows, cols = len(data), len(data[0])
    table = doc.add_table(rows=rows, cols=cols)
    table.style = 'Table Grid'
    for i, row_data in enumerate(data):
        for j, cell_text in enumerate(row_data):
            cell = table.cell(i, j)
            cell.text = ''
            p = cell.paragraphs[0]
            run = p.add_run(str(cell_text))
            run.font.size = Pt(9.5)
            if i == 0:  # Header row
                run.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                set_cell_shading(cell, '2B579A')
            elif i % 2 == 0:  # Even rows
                set_cell_shading(cell, 'F2F2F2')
    return table
```

### 3.3 各级标题

```python
# 一级标题（节标题）
run.font.size = Pt(14); run.bold = True; color = RGBColor(0x1A, 0x1A, 0x2E)

# 二级标题（子标题）
run.font.size = Pt(12); run.bold = True; color = RGBColor(0x2B, 0x57, 0x9A)

# 三级标题（层级标题，如【基础巩固】）
run.font.size = Pt(12); run.bold = True; color = RGBColor(0xC0, 0x39, 0x2B)
```

### 3.4 引用文本（灰色缩进斜体）

```python
p.paragraph_format.left_indent = Cm(1)
run.font.size = Pt(10)
run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
run.italic = True
```

## 四、样式色板

| 用途 | 色值 | 说明 |
|:-----|:-----|:-----|
| 一级标题 | #1A1A2E | 深藏青 |
| 二级标题 | #2B579A | 中蓝 |
| 三级分层标题 | #C0392B | 红色（区分层级） |
| 表头背景 | #2B579A | 与二级标题色一致 |
| 交替行背景 | #F2F2F2 | 浅灰 |
| 引用文本 | #555555 | 中灰 |

## 五、已知限制

- python-docx不支持嵌套列表转换为Word多级列表（需手动调整）
- 复杂表格（合并单元格、跨行列）需在Word中手动微调
- 代码块格式在Word中需手动设置等宽字体
- 生成的.docx文件可在WPS和Microsoft Word中正常打开

## 六、典型工作流

```bash
# 1. 在markdown中编写完整作业设计
# 2. 运行python-docx转换脚本
python create_docx.py
# 3. 在Word中打开检查：
#    - 表格是否完整
#    - 分页是否合理
#    - 页眉页脚
#    - 目录（如需要）
# 4. 微调后另存为提交格式
```
