#!/usr/bin/env python3
"""Batch OCR for scanned math textbooks using RapidOCR - v2 fixed"""
import os, sys, json, time, glob, subprocess, tempfile, shutil

PDFS = {
    "八上": "E:/初中数学新教材/2025秋人教版八年级数学上册.pdf",
    "八下": "E:/初中数学新教材/2026春人教版八年级数学下册电子课本.pdf",
    "九上": "E:/初中数学新教材/2026秋 数学（人教版）九年级上册（彩色清晰版）(1).pdf",
}

OUT_DIR = "E:/初中数学新教材/ocr_output"
os.makedirs(OUT_DIR, exist_ok=True)
log_path = os.path.join(OUT_DIR, "ocr_batch_log_v2.txt")

sys.setrecursionlimit(10000)

def log(msg):
    t = time.strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    print(line)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_page_count(pdf_path):
    """Get page count using pdfminer (avoids pdfinfo subprocess issues)"""
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdfdocument import PDFDocument
    try:
        with open(pdf_path, "rb") as f:
            parser = PDFParser(f)
            doc = PDFDocument(parser)
            return len(list(doc.get_pages()))
    except:
        pass
    # Fallback: use pdftoppm to count by trying page 200
    try:
        for n in [300, 250, 200, 150, 100]:
            r = subprocess.run(["pdftoppm", "-f", str(n), "-l", str(n), "-png", 
                               pdf_path, os.path.join(tempfile.mkdtemp(), "t")],
                              capture_output=True, timeout=30)
            if r.returncode == 0:
                return n
    except:
        pass
    return 200  # conservative guess

def ocr_page(engine, img_path):
    result, elapse = engine(img_path)
    if not result:
        return ""
    lines = [line[1] for line in result]
    return "\n".join(lines)

def process_pdf(name, pdf_path):
    log(f"开始处理 {name}")
    
    pages = get_page_count(pdf_path)
    log(f"{name}: 检测到 {pages} 页")
    
    work_dir = tempfile.mkdtemp(prefix=f"ocr_{name}_")
    
    # Init RapidOCR once per book
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    
    all_text = []
    batch_size = 5  # Smaller batch for stability
    
    for start in range(1, pages + 1, batch_size):
        end = min(start + batch_size - 1, pages)
        
        try:
            r = subprocess.run(
                ["pdftoppm", "-f", str(start), "-l", str(end), "-png", "-r", "200",
                 pdf_path, os.path.join(work_dir, "p")],
                capture_output=True, timeout=120
            )
        except Exception as e:
            log(f"  pdftoppm batch {start}-{end} 失败: {e}")
            continue
        
        # Collect images in order
        for i in range(start, end + 1):
            candidates = glob.glob(os.path.join(work_dir, f"p-{i:06d}*.png"))
            if not candidates:
                candidates = glob.glob(os.path.join(work_dir, f"p-{i:05d}*.png"))
            if not candidates:
                candidates = glob.glob(os.path.join(work_dir, f"p-{i:04d}*.png"))
            if not candidates:
                candidates = glob.glob(os.path.join(work_dir, f"p-{i:03d}*.png"))
            if not candidates:
                candidates = glob.glob(os.path.join(work_dir, f"p-{i:02d}*.png"))
            if not candidates:
                candidates = glob.glob(os.path.join(work_dir, f"p-{i:01d}*.png"))
            
            if not candidates:
                log(f"  {name} 第{i}页: 图片未生成 ⚠️")
                continue
            
            try:
                text = ocr_page(engine, candidates[0])
                all_text.append(f"\n\n=== PAGE {i} ===\n{text}")
                if text.strip():
                    log(f"  {name} 第{i}页: {len(text)}字符 ✅")
                else:
                    log(f"  {name} 第{i}页: 空白 ⚠️")
            except Exception as e:
                log(f"  {name} 第{i}页: OCR失败 ❌ {e}")
            
            # Clean up image
            try: os.remove(candidates[0])
            except: pass
        
        # Save progress every batch
        if start % 20 == 0 or end >= pages:
            save_path = os.path.join(OUT_DIR, f"{name}_ocr.txt")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write("".join(all_text))
            log(f"  {name}: 已保存前{end}页 ({len(''.join(all_text))}字符)")
    
    # Final save
    save_path = os.path.join(OUT_DIR, f"{name}_ocr.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write("".join(all_text))
    
    total_chars = len("".join(all_text))
    log(f"✅ {name} 完成! {pages}页, {total_chars}字符 → {save_path}")
    shutil.rmtree(work_dir, ignore_errors=True)
    return save_path

if __name__ == "__main__":
    log("=" * 50)
    log("Batch OCR v2 启动")
    log("=" * 50)
    
    try:
        from rapidocr_onnxruntime import RapidOCR
        log("RapidOCR 可用 ✅")
    except Exception as e:
        log(f"RapidOCR 加载失败: {e}")
        sys.exit(1)
    
    for name, pdf_path in PDFS.items():
        if not os.path.exists(pdf_path):
            log(f"⚠️ {name}: 文件不存在")
            continue
        
        done_path = os.path.join(OUT_DIR, f"{name}_ocr.txt")
        if os.path.exists(done_path) and os.path.getsize(done_path) > 2000:
            log(f"{name}: 已有结果，跳过 ({os.path.getsize(done_path)}字节)")
            continue
        
        try:
            process_pdf(name, pdf_path)
        except Exception as e:
            log(f"{name}: 处理失败 ❌ {e}")
            import traceback
            log(traceback.format_exc())
    
    log("=" * 50)
    log("全部完成!")
    log("=" * 50)
