# BKT贝叶斯知识追踪 实现参考（2026-07-24）

**服务器：** 学霸基本法 ECS 8.145.57.233
**文件位置：** `/opt/xueba/server/services/knowledge_graph.py`
**添加时间：** 2026-07-24

## BKT模型参数

```
DEFAULT_BKT_PARAMS = {
    "initial_p": 0.30,   # 初始掌握概率
    "learn_rate": 0.60,  # 学习转移概率
    "guess": 0.15,       # 猜测概率
    "slip": 0.10,        # 失误概率
    "mastery": 0.85,     # 掌握阈值
    "forget": 0.02,      # 遗忘率
}
```

## 贝叶斯更新公式

做对了：P(mastery | correct) = P(correct|mastery)×P(mastery) / P(correct)
做错了：P(mastery | wrong) = P(wrong|mastery)×P(mastery) / P(wrong)

详见 `knowledge_graph.py` 中 `BKTTracker.update()` 方法。

## 存储

SQLite `xueba.db` 中的 `bkt_probs` 表：
- student_id, knowledge (联合主键)
- probability (当前概率)
- answer_count, correct_count
- last_updated

## API端点

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/api/v2/knowledge/bkt/update` | 报告答题结果 |
| GET | `/api/v2/knowledge/bkt/weak` | 薄弱点列表 |
| GET | `/api/v2/knowledge/bkt/all` | 全部状态 |

## 验证数据

学生 test001，知识点"勾股定理"：对(0.30→0.737) 对(0.737→0.947→mastered) 错(0.947→0.698)
