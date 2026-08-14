"""数学作业OCR管道：图片→识别→拆题→诊断→评估"""
import json, os, tempfile, subprocess, time, logging, re
from pathlib import Path

logger = logging.getLogger("xueba.ocr_pipeline")

def run_pipeline(file_bytes: bytes, filename: str, llm_client) -> dict:
    """完整流程"""
    t0 = time.monotonic()
    # 1. 保存图片 → 2. OCR识别 → 3. 逐题拆分 → 4. DeepSeek诊断 → 5. 综合评价
    # 见 SKILL.md 中的架构图
    return {"elapsed_ms": int((time.monotonic()-t0)*1000)}

def split_into_problems(text: str) -> list:
    """按题号拆分为单题列表"""
    results = []
    parts = re.split(r'(?:^|\n)\s*(?:第[一二三四五六七八九十]题|[\(（]?\d+[\)）]\.?)', text, flags=re.MULTILINE)
    for i, part in enumerate(parts):
        part = part.strip()
        if part and len(part) > 5:
            results.append({"number": i+1, "text": part})
    return results

def comprehensive_evaluation(problems: list, llm_client=None) -> dict:
    """综合评价"""
    total = len(problems)
    errors = [p for p in problems if p.get("error_types")]
    stats = {}
    for p in errors:
        for et in p.get("error_types", []):
            stats[et] = stats.get(et, 0) + 1
    return {
        "total_problems": total,
        "correct_count": total - len(errors),
        "error_count": len(errors),
        "error_distribution": stats,
        "score": f"{total - len(errors)}/{total}",
        "grade": "优秀" if (total - len(errors))/total >= 0.9 else "良好" if (total - len(errors))/total >= 0.75 else "及格" if (total - len(errors))/total >= 0.6 else "需努力",
    }
