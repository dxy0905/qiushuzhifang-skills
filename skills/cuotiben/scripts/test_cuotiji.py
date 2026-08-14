#!/usr/bin/env python3
"""测试错题集API"""
import requests, sys, json

BASE = "http://127.0.0.1:8080"  # 重构版start_server.py: port=8080

def test_health():
    r = requests.get(f"{BASE}/api/health", timeout=5)
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("✅ 服务器正常")

def test_review():
    for period in ["week", "month", "semester"]:
        r = requests.post(f"{BASE}/api/v2/review/generate",
            json={"period": period, "limit": 5}, timeout=10)
        data = r.json().get("data", r.json())
        assert "cards" in data, f"Missing cards for {period}"
        print(f"✅ {data.get('period_label','?')}: {data.get('total',0)}题 -> {data.get('selected',0)}题选中")
    print("✅ 错题集API正常")

def test_knowledge():
    r = requests.get(f"{BASE}/api/v2/knowledge/topics", timeout=5)
    topics = r.json().get("data", {}).get("topics", [])
    count = sum(t.get("count", 0) for t in topics)
    print(f"✅ 知识库: {len(topics)}知识点, {count}条错误模式")
    return count > 0

if __name__ == "__main__":
    try:
        test_health()
        test_knowledge() and test_review()
        print("\n✅ 全部通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
