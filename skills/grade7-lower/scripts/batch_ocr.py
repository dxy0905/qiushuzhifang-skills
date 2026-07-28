#!/usr/bin/env python3
"""Batch OCR for scanned math textbooks using RapidOCR"""
import os, sys, json, time, glob

PDFS = {
    "七上": "E:/初中数学新教材/2024新人教版数学七上课本彩板（无水印）.pdf",
    "八上": "E:/初中数学新教材/2025秋人教版八年级数学上册.pdf",
    "八下": "E:/初中数学新教材/2026春人教版八年级数学下册电子课本.pdf",
    "九上": "E:/初中数学新教材/2026秋 数学（人教版）九年级上册（彩色清晰版）(1).pdf",
}

OUT_DIR = "E:/初中数学新教材/ocr_output"
os.makedirs(OUT_DIR, exist_ok=True)

# Log file
log_path = os.path.join(OUT_DIR, "ocr_batch_log.txt")

def log(msg):
    t = time.strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    print(line)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def ocr_page(img_path):
    """OCR a single page image and return text"""
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    result, elapse = engine(img_path)
    if not result:
        return ""
    lines = [line[1] for line in result]
    return "\n".join(lines)

def process_pdf(name, pdf_path):
    """Process a scanned PDF: pdftoppm -> RapidOCR -> save text"""
    import tempfile, subprocess
    
    log(f"开始处理 {name} ({pdf_path})")
    
    # Create temp dir for page images
    work_dir = tempfile.mkdtemp(prefix=f"ocr_{name}_")
    
    # Get page count
    result = subprocess.run(
        ["pdfinfo", pdf_path],
        capture_output=True, text=True, timeout=30
    )
    pages = 0
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split(":")[1].strip())
            break
    
    log(f"{name}: 共 {pages} 页")
    
    all_text = []
    batch_size = 10  # Convert 10 pages at a time
    
    for start in range(1, pages + 1, batch_size):
        end = min(start + batch_size - 1, pages)
        
        # Convert batch of pages to images
        subprocess.run(
            ["pdftoppm", "-f", str(start), "-l", str(end), "-png", "-r", "200",
             pdf_path, os.path.join(work_dir, f"page")],
            capture_output=True, timeout=120
        )
        
        # Get the image files in order
        img_files = sorted(glob.glob(os.path.join(work_dir, "page-*.png")))
        
        for i, img_path in enumerate(img_files):
            page_num = start + i
            try:
                text = ocr_page(img_path)
                all_text.append(f"\n\n=== PAGE {page_num} ===\n{text}")
                if text.strip():
                    log(f"  {name} 第{page_num}页: {len(text)}字符 ✅")
                else:
                    log(f"  {name} 第{page_num}页: 空白 ⚠️")
            except Exception as e:
                log(f"  {name} 第{page_num}页: 失败 ❌ {e}")
            
            # Clean up image file immediately
            try:
                os.remove(img_path)
            except:
                pass
        
        # Save progress periodically
        save_path = os.path.join(OUT_DIR, f"{name}_ocr.txt")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("".join(all_text))
        log(f"  {name}: 已保存前{end}页到 {save_path}")
    
    # Final save
    save_path = os.path.join(OUT_DIR, f"{name}_ocr.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write("".join(all_text))
    
    total_chars = sum(len(t) for t in all_text)
    log(f"{name} 完成! 共 {pages} 页, {total_chars} 字符 → {save_path}")
    
    # Cleanup temp dir
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)
    
    return save_path

if __name__ == "__main__":
    log("=" * 50)
    log("Batch OCR 启动")
    log("=" * 50)
    
    # Check RapidOCR
    try:
        from rapidocr_onnxruntime import RapidOCR
        log("RapidOCR 可用 ✅")
    except Exception as e:
        log(f"RapidOCR 加载失败: {e}")
        sys.exit(1)
    
    # Process each PDF
    for name, pdf_path in PDFS.items():
        if not os.path.exists(pdf_path):
            log(f"⚠️ {name}: 文件不存在 {pdf_path}")
            continue
        
        # Check if already done
        done_path = os.path.join(OUT_DIR, f"{name}_ocr.txt")
        if os.path.exists(done_path) and os.path.getsize(done_path) > 1000:
            log(f"{name}: 已有OCR结果，跳过 ({done_path})")
            continue
        
        try:
            process_pdf(name, pdf_path)
        except Exception as e:
            log(f"{name}: 处理失败 ❌ {e}")
    
    log("=" * 50)
    log("全部处理完成!")
    log("=" * 50)
