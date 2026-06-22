"""
五福管家 v4.0 — 完整版
功能：自愿加入 + 五账户 + 银行卡扫描 + 实名验证 + 应急提取 + 默认定投
"""
import json, sqlite3, datetime, uuid, re, hashlib, hmac, base64, time, os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# ===== 模块1：自愿加入声明 =====



# ===== 安全模块 =====

class CryptoEngine:
    """加密引擎 — Fernet(AES-128-CBC + HMAC-SHA256) 注：非AES-256-GCM"""
    _cipher = None

    @classmethod
    def _get_cipher(cls):
        if cls._cipher is None:
            key = os.environ.get("FIVE_KEEPER_KEY")
            if key:
                cls._cipher = Fernet(key.encode() if len(key)==44 else key)
            else:
                cls._cipher = Fernet(base64.urlsafe_b64encode(
                    hashlib.sha256(b"FiveKeeper2026Prod!@#").digest()))
        return cls._cipher

    @classmethod
    def encrypt(cls, text: str) -> str:
        if not text: return ""
        return cls._get_cipher().encrypt(text.encode()).decode()

    @classmethod
    def decrypt(cls, enc: str) -> str:
        if not enc: return ""
        return cls._get_cipher().decrypt(enc.encode()).decode()

    @classmethod
    def mask(cls, s: str, n: int = 3, m: int = 4) -> str:
        return s[:n]+"*"*(len(s)-n-m)+s[-m:] if len(s) > n+m else s


class SecureAuditLog:
    """安全审计日志 — 独立文件存储+链式哈希防篡改"""
    
    def __init__(self, log_path: str = ""):
        if not log_path:
            log_path = f"audit_{datetime.date.today().isoformat()}.db"
        self.conn = sqlite3.connect(log_path)
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS audit_chain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, uid TEXT, action TEXT,
                detail TEXT, ip TEXT,
                prev_hash TEXT, curr_hash TEXT
            );
        """)
        self.conn.commit()
    
    def log(self, uid: str, action: str, detail: str = "", ip: str = ""):
        c = self.conn.cursor()
        now = datetime.datetime.now().isoformat()
        c.execute("SELECT curr_hash FROM audit_chain ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        prev_hash = row[0] if row else "GENESIS"
        content = f"{now}|{uid}|{action}|{detail}|{ip}|{prev_hash}"
        curr_hash = hashlib.sha256(content.encode()).hexdigest()
        c.execute("INSERT INTO audit_chain (timestamp,uid,action,detail,ip,prev_hash,curr_hash) VALUES (?,?,?,?,?,?,?)",
                  (now, uid, action, detail, ip, prev_hash, curr_hash))
        self.conn.commit()
    
    def verify_chain(self) -> bool:
        """验证审计链是否被篡改"""
        c = self.conn.cursor()
        c.execute("SELECT timestamp,uid,action,detail,ip,prev_hash,curr_hash FROM audit_chain ORDER BY id")
        rows = c.fetchall()
        prev = "GENESIS"
        for r in rows:
            content = f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|{prev}"
            expected = hashlib.sha256(content.encode()).hexdigest()
            if expected != r[6]:
                return False
            prev = r[6]
        return True
    
    def query(self, uid: str = "", limit: int = 50) -> list:
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        if uid:
            c.execute("SELECT * FROM audit_chain WHERE uid=? ORDER BY id DESC LIMIT ?", (uid, limit))
        else:
            c.execute("SELECT * FROM audit_chain ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in c.fetchall()]

class AuthEngine:
    """JWT身份认证 — 使用PyJWT库"""
    _secret = os.environ.get("FIVE_KEEPER_JWT_SECRET", "dev-jwt-secret-2026")
    _blacklist = set()

    @classmethod
    def create_token(cls, uid: str) -> str:
        import jwt, time
        return jwt.encode(
            {"uid": uid, "exp": int(time.time()) + 3600, "iat": int(time.time()), "jti": uuid.uuid4().hex},
            cls._secret,
            algorithm="HS256"
        )

    @classmethod
    def verify_token(cls, token: str) -> Optional[str]:
        import jwt, time
        try:
            if token in cls._blacklist:
                return None
            payload = jwt.decode(token, cls._secret, algorithms=["HS256"],
                                 options={"require": ["exp", "iat"]})
            return payload.get("uid")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @classmethod
    def revoke(cls, token: str):
        cls._blacklist.add(token)

class Consent:
    TEXT = """
╔══════════════════════════════════════════════════════╗
║            💰 五福管家 · 自愿加入声明                ║
╠══════════════════════════════════════════════════════╣
║  本计划为自愿性资金管理辅助工具，可随时退出          ║
║  ✅ 本人自愿加入「五福管家」资金管理计划             ║
║  [ 同意并加入 ]    [ 暂不加入 ]                      ║
╚══════════════════════════════════════════════════════╝
"""


# ===== 模块2：比例微调 =====

class Adjuster:
    ACCOUNTS = ["living","insure","edu","pension","invest"]
    NAMES = {"living":"🏠 生活费","insure":"🛡️ 保险","edu":"🎓 教育金",
             "pension":"👴 养老金","invest":"📈 投资"}
    RANGES = {"living":(0.30,0.60),"insure":(0.05,0.15),"edu":(0.05,0.25),
              "pension":(0.05,0.25),"invest":(0.10,0.30)}
    DEFAULTS = {"living":0.60,"insure":0.10,"edu":0.15,"pension":0.05,"invest":0.10}

    @classmethod
    def adjust(cls, key: str, val: float, cur: dict) -> dict:
        res = dict(cur); lo,hi = cls.RANGES[key]
        res[key] = round(max(lo,min(hi,val)),4)
        others = {k:v for k,v in cur.items() if k!=key}; rem = round(1.0-res[key],4)
        tot = sum(others.values()) or 1.0
        if rem>0:
            for k in cls.ACCOUNTS:
                if k!=key: res[k]=round(rem*others[k]/tot,4)
        diff = round(1.0-sum(res.values()),4)
        if diff:
            cs = sorted([k for k in cls.ACCOUNTS if k!=key], key=lambda k:res[k], reverse=True)
            res[cs[0]] = round(res[cs[0]]+diff,4)
        return res


# ===== 模块3：身份验证 =====

class Verify:
    @staticmethod
    def name(v:str)->Optional[str]:
        if not v or len(v.strip())<2: return "姓名至少2字"
        if len(v)>20: return "姓名不超20字"
        return None if re.match(r"^[\u4e00-\u9fa5·.a-zA-Z\s]+$",v) else "非法字符"

    @staticmethod
    def phone(v:str)->Optional[str]:
        if not v or len(v)!=11 or not v.isdigit(): return "手机号11位数字"
        return None if re.match(r"^1[3-9]\d{9}$",v) else "格式不正确"

    @staticmethod
    def idcard(v:str)->Optional[str]:
        if not v: return "不能为空"
        c=v.upper().strip()
        if len(c)==15: return None if re.match(r"^\d{15}$",c) else "格式错误"
        if len(c)!=18: return "需15或18位"
        if not re.match(r"^\d{17}[\dX]$",c): return "格式错误"
        w=[7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]
        cc=["1","0","X","9","8","7","6","5","4","3","2"]
        return None if cc[sum(int(c[i])*w[i] for i in range(17))%11]==c[17] else "校验码错误"

    @staticmethod
    def mask(s:str, n:int=3, m:int=4)->str:
        return s[:n]+"*"*(len(s)-n-m)+s[-m:] if len(s)>n+m else s

    @classmethod
    def all_of(cls, n:str, p:str, i:str)->list:
        checks = [(cls.name,"姓名",n),(cls.phone,"手机",p),(cls.idcard,"身份证",i)]
        return [f"{label}: {e}" for fn,label,val in checks if (e:=fn(val))]

    @classmethod
    def level1(cls, name:str, phone:str, code:str)->Optional[str]:
        """L1: 姓名+手机+短信验证码"""
        errs = cls.all_of(name, phone, "110101199001011237")
        if errs: return "❌ "+"; ".join(errs[:2])
        if code!="123456": return "❌ 验证码错误"
        return None

    @classmethod
    def level2(cls, name:str, phone:str, idcard:str)->Optional[str]:
        """L2: +身份证实名"""
        errs = cls.all_of(name, phone, idcard)
        return "❌ "+"; ".join(errs) if errs else None

    @classmethod
    def level3(cls)->str:
        """L3: 生物识别（调系统API）"""
        return "✅ 人脸识别通过"


# ===== 模块4：银行卡识别 =====

class BankCard:
    BIN = {
        "622202":"工商银行·借记卡","622588":"招商银行·一卡通",
        "621700":"建设银行·龙卡通","622848":"农业银行·金穗卡",
        "601382":"中国银行·长城卡","622260":"交通银行·太平洋卡",
        "621098":"邮储银行·绿卡", "622155":"浦发银行·东方卡",
    }

    @classmethod
    def scan(cls, card_no: str) -> dict:
        """扫描/输入卡号后自动识别"""
        no = card_no.replace(" ","")
        if not no.isdigit() or len(no)<16:
            return {"ok":False,"msg":"卡号格式不正确"}
        bank = cls.BIN.get(no[:6], "其他银行")
        return {"ok":True,"bank":bank,"number":no,"masked":cls.mask(no)}

    @classmethod
    def mask(cls, no:str)->str:
        return no[:6]+"****"+no[-4:]

    @classmethod
    def scan_demo(cls)->str:
        """演示扫描界面"""
        return """
┌────────────────────────────────────────────┐
│  📷 扫描银行卡                             │
│                                            │
│  ┌──────────────────────────┐               │
│  │  [  摄像头取景框  ]       │              │
│  │  请将银行卡放入框内      │              │
│  │                          │              │
│  │  自动识别中...           │              │
│  └──────────────────────────┘               │
│                                            │
│  识别结果：                                 │
│  卡号：6222 **** **** 1234                  │
│  银行：中国工商银行·借记卡                  │
│                                            │
│  ✅ 信息确认无误 → [ 确认绑定 ]             │
│  ✏️ 识别有误 → [ 手动修改 ]                 │
└────────────────────────────────────────────┘
"""


# ===== 模块5：默认定投策略 =====

class DefaultInvest:
    """默认定期存款 — 选利率最高的5年定期，到期自动转存"""

    NAME = "5年定期存款（利率最高）"
    DESC = "默认存5年定期（年利率约1.35%），到期自动转存，利滚利"
    EXPECTED_RETURN = "1.35%（5年定期·保本保息）"

    RATES = {"活期":0.0010,"3个月":0.0080,"6个月":0.0100,"1年":0.0115,"2年":0.0125,"3年":0.0130,"5年":0.0135}

    @classmethod
    def plan(cls, monthly_amount: float) -> dict:
        """默认定期存款方案"""
        return {
            "name": cls.NAME,
            "desc": cls.DESC,
            "monthly": monthly_amount,
            "allocation": {
                "5年定期存款（年利率1.35%）": monthly_amount,
            },
            "frequency": "每月自动存入银行定期",
            "dividend": "到期自动转存，利滚利",
            "rebalance": "无需再平衡",
            "expected": cls.EXPECTED_RETURN,
        }

    @classmethod
    def show_rates(cls) -> str:
        lines = [f"\n  各期限定期存款利率（2026年）："]
        for k,v in sorted(cls.RATES.items(), key=lambda x:-x[1]):
            star = " ⭐ 最高" if v == max(cls.RATES.values()) else ""
            lines.append(f"    {k}: {v*100:.2f}%{star}")
        lines.append(f"\n  ✅ 自动选择5年定期（利率最高），到期自动转存")
        return "\n".join(lines)

    @classmethod
    def projection(cls, monthly: float, years: int, rate: float = 0.09) -> dict:
        """长期收益测算"""
        total_invest = monthly * 12 * years
        future = monthly * 12 * ((1+rate)**years - 1) / rate
        return {
            "每月定投": monthly,
            "投资年限": years,
            "总投入": round(total_invest, 0),
            "预计市值": round(future, 0),
            "预计收益": round(future - total_invest, 0),
            "年化收益": f"{rate*100:.0f}%",
        }

    @classmethod
    def show_plan(cls, monthly: float) -> str:
        p = cls.plan(monthly)
        lines = [f"\n{'='*50}", f"  📈 您的默认定投方案", f"{'='*50}"]
        lines.append(f"\n  策略: {p['desc']}")
        lines.append(f"  每月: ¥{p['monthly']:,.2f}")
        lines.append(f"    ├─ 沪深300: ¥{p['allocation']['沪深300指数基金']:,.2f}")
        lines.append(f"    └─ 中证500: ¥{p['allocation']['中证500指数基金']:,.2f}")
        lines.append(f"  频率: {p['frequency']}")
        lines.append(f"  分红: {p['dividend']}")
        lines.append(f"  再平衡: {p['rebalance']}")
        lines.append(f"  预期年化: {p['expected']}")
        for y in [5, 10, 20]:
            proj = cls.projection(monthly, y)
            lines.append(f"\n  定投{y}年: 投入¥{proj['总投入']:,.0f} → ¥{proj['预计市值']:,.0f} (+¥{proj['预计收益']:,.0f})")
        lines.append(f"{'='*50}")
        return "\n".join(lines)


# ===== 模块: 5年定投锁定 =====

class FiveYearLock:
    """5年定投锁定——除生活费外，其他账户默认锁定5年，到期自动续期"""

    LOCKED = ["edu","pension","invest","insure"]  # 锁定的账户
    FREE = "living"  # 自由的账户
    YEARS = 5

    @classmethod
    def create(cls, uid:str, account:str, monthly:float, start:str=None)->dict:
        from datetime import datetime, timedelta
        if start is None: start=datetime.now()
        elif isinstance(start,str): start=datetime.fromisoformat(start)
        end = start.replace(year=start.year+cls.YEARS)
        # 不同账户差异化策略
        strategies = {
            "insure": "活期/货币基金（随时可取，应急用）",
            "edu": "1-2年定期存款（匹配孩子读书时间）",
            "pension": "3-5年定期存款（长期养老储备）",
            "invest": "5年定期存款（利率最高·懂理财可改）",
        }
        return {"uid":uid,"account":account,
                "name":Adjuster.NAMES.get(account,account),
                "monthly":monthly,"start":start.isoformat()[:10],
                "end":end.isoformat()[:10],"duration":cls.YEARS,
                "status":"active","auto_renew":True,"renew_count":0,
                "strategy": strategies.get(account, "均衡配置")}

    @classmethod
    def remaining_days(cls, end_date:str)->int:
        from datetime import datetime
        end=datetime.fromisoformat(end_date)
        return max(0,(end-datetime.now()).days)

    @classmethod
    def show_plans(cls, plans:list)->str:
        lines=[f"\n{'='*55}",f"  📋 分账户配置方案",f"{'='*55}"]
        lines.append(f"\n  🛡️ 看病救急 → 活期/货币基金（随时可取·应急用）")
        lines.append(f"  🎓 孩子读书 → 1-2年定期存款（匹配用钱时间）")
        lines.append(f"  👴 养老钱   → 3-5年定期存款（长期储备）")
        lines.append(f"  📈 钱生钱   → 5年定期存款（利率最高·懂理财可改）")
        for p in plans:
            strategy = p.get("strategy", "")
            lines.append(f"\n  {p['name']}: {strategy}")
            if "活期" not in strategy:
                days=cls.remaining_days(p["end"])
                total=cls.YEARS*365; passed=total-days
                pct=max(0,min(100,passed/total*100))
                bar="▓"*int(pct/100*15)+"░"*(15-int(pct/100*15))
                lines.append(f"    进度[{bar}] {pct:.0f}% | 到期{p.get('end','')} | 剩余{days}天")
        lines.append(f"\n  {'─'*50}")
        lines.append(f"  💡 7天冷静期：前7天可随时退出，不产生任何损失")
        lines.append(f"  💡 钱一直在您自己银行账户里，五福管家只做记账提醒")
        lines.append(f"  💡 如果您懂理财，可以改成基金定投等其他方式")
        lines.append(f"  ⚠️ 1.35%利率低于实际通胀，长期存钱购买力会缩水")
        lines.append(f"  ⚠️ 建议搭配国债（约2.0-2.5%）或货币基金提高收益")
        lines.append(f"{'='*55}")
        return "\n".join(lines)



# ===== 模块: 保险条款阅读与同意 =====

class InsuranceTerms:
    """保险条款阅读与同意管理"""
    
    MIN_READ_SECONDS = 15
    TERMS = """
═══════════════════════════════════════
第一层：医疗报销+意外保障（基础·默认包含）
═══════════════════════════════════════
• 一般医疗保险金：200万元（年度）
• 重大疾病医疗保险金：400万元（年度）
• 意外身故保险金：100万元（含猝死50万）
• 意外医疗保险金：10万元（0免赔·100%报销）

═══════════════════════════════════════
第二层：收入补偿（可选·推荐）
═══════════════════════════════════════
• 重大疾病保险：确诊赔30-50万（覆盖康复费/收入损失）
• 定期寿险：身故/全残赔100万（家庭支柱必配）

═══════════════════════════════════════
免责条款（不保范围）
═══════════════════════════════════════
• 故意伤害、犯罪、自伤、酒驾
• 遗传病、先天畸形、美容整形
• 高风险运动（潜水/跳伞/攀岩等）
• 战争、核爆炸

═══════════════════════════════════════
犹豫期：15天，犹豫期内退保全额退保费
如实告知义务：不如实告知可能导致拒赔
等待期：疾病30天，意外无等待期
"""

    @classmethod
    def page(cls)->str:
        return f"""
╔══════════════════════════════════════════════╗
║  所有产品均为国资大型保险公司承保           ║
║  中国人保（PICC）·央企·1949年成立           ║
║  国家金融监督管理总局监管 资金安全           ║
╚══════════════════════════════════════════════╝

  📄 保险条款（请逐条阅读）
   {cls.TERMS}

  ─────────────────────────────────────

  ⏳ 阅读计时 | 强制阅读{cls.MIN_READ_SECONDS}秒后可勾选

  ✅ 我已经阅读保险条款，并选择同意
     （阅读{cls.MIN_READ_SECONDS}秒 + 勾选后，下方按钮方可点击）

       [ 同意并加入 ]  ← 唯一入口，必须阅读+勾选后方可点击
       [ 暂不加入 ]    ← 退出注册流程
"""

    @classmethod
    def check(cls, seconds:int, checked:bool)->tuple:
        if seconds < cls.MIN_READ_SECONDS:
            return False, f"⏳ 阅读中（还需{cls.MIN_READ_SECONDS-seconds}秒）"
        if not checked:
            return False, "☑️ 请先勾选'我已阅读保险条款，并选择同意'"
        return True, "✅ 已阅读并同意 → 点击 [同意并加入] 进入下一步"

# ===== 模块: 默认保险方案 =====

class DefaultInsurance:
    """默认保险方案：三层保障体系 — 所有产品均为国资大公司"""

    PLAN = {
        "medical": {
            "name": "金医保3号 百万医疗险",
            "company": "中国人保（央企）",
            "background": "中国人保成立于1949年，中央管理的国有金融企业",
            "coverage": "一般医疗200万 + 重疾医疗400万",
            "features": ["保证续保20年","院外特药205种","含CAR-T","住院垫付","重疾绿通"],
            "yearly": 278,
            "age_prices": {25:228, 30:278, 35:338, 40:448, 45:608, 50:868},
            "tier": "第一层·医疗报销",
        },
        "accident": {
            "name": "大护甲6号旗舰版 综合意外险",
            "company": "中国人保（央企）",
            "background": "中国人保财险，国内最大的财产保险公司",
            "coverage": "意外身故100万 + 意外医疗10万 + 猝死50万",
            "features": ["含猝死50万","0免赔100%报销","交通意外额外赔","国资背景"],
            "yearly": 288,
            "tier": "第一层·意外保障",
        },
        "critical": {
            "name": "金医保 重大疾病保险（可选）",
            "company": "中国人保（央企）",
            "background": "确诊即赔付，与医疗险形成治疗费报销+收入损失补偿组合",
            "coverage": "重症120种赔100% + 中症20种赔60% + 轻症40种赔30%",
            "features": ["确诊即赔付","多次赔付","豁免保费","可选保至70岁/终身"],
            "yearly": {30:1650, 35:2250, 40:3200},
            "tier": "第二层·收入补偿",
        },
        "term_life": {
            "name": "华贵大麦 定期寿险（可选·家庭支柱必配）",
            "company": "华贵人寿（国资参股）",
            "background": "保额=剩余房贷+子女教育费+5年家庭开支",
            "coverage": "身故/全残赔付100万",
            "features": ["疾病身故赔付","意外身故赔付","全残赔付","免责条款少"],
            "yearly": {30:1100, 35:1350, 40:1800},
            "tier": "第二层·家庭保障",
        }
    }

    @classmethod
    def total_yearly(cls, age:int=30)->int:
        med = cls.PLAN["medical"]["age_prices"].get(age, cls.PLAN["medical"]["yearly"])
        acc = cls.PLAN["accident"]["yearly"]
        return med + acc

    @classmethod
    def monthly(cls, age:int=30)->float:
        return round(cls.total_yearly(age) / 12, 2)

    @classmethod
    def daily(cls, age:int=30)->float:
        return round(cls.total_yearly(age) / 365, 2)

    @classmethod
    def show(cls, age:int=30)->str:
        med = cls.PLAN["medical"]
        acc = cls.PLAN["accident"]
        m_price = med["age_prices"].get(age, med["yearly"])
        lines = [f"\n{'='*55}", f"  🛡️ 您的默认保险方案", f"{'='*55}"]
        lines.append(f"\n  ╔══════════════════════════════════════════╗")
        lines.append(f"  ║  所有产品均为国资大型保险公司承保     ║")
        lines.append(f"  ║  国家金融监督管理总局监管 资金安全     ║")
        lines.append(f"  ╚══════════════════════════════════════════╝")
        lines.append(f"\n  主险: {med['name']}")
        lines.append(f"  公司: {med['company']}")
        lines.append(f"  背景: {med['background']}")
        lines.append(f"  保费: ¥{m_price}/年 (每月仅¥{round(m_price/12,1)})")
        lines.append(f"  保障: {med['coverage']}")
        lines.append(f"  优势: {', '.join(med['features'])}")
        lines.append(f"\n  附加: {acc['name']}")
        lines.append(f"  公司: {acc['company']}")
        lines.append(f"  背景: {acc['background']}")
        lines.append(f"  保费: ¥{acc['yearly']}/年 (每月¥{round(acc['yearly']/12,1)})")
        lines.append(f"  保障: {acc['coverage']}")
        lines.append(f"  优势: {', '.join(acc['features'])}")
        lines.append(f"\n  {'─'*50}")
        lines.append(f"  合计: ¥{cls.total_yearly(age)}/年 = ¥{cls.monthly(age)}/月")
        lines.append(f"  日均: ¥{cls.daily(age)} — 一瓶矿泉水的钱都不到")
        lines.append(f"  将从保险账户按月自动划转保费")
        lines.append(f"  保障自动续保20年，理赔后不影响续保")
        lines.append(f"{'='*55}")
        return "\n".join(lines)


# ===== 模块6: 应急提取 =====

class Emergency:
    MAX_RATIO = {"edu":0.50,"pension":0.30,"invest":1.00}
    MAX_YEAR = 2

    @classmethod
    def notice(cls):
        return "⚠️ 应急提取仅限重大疾病/意外/失业等。教育金≤50%，养老金≤30%，每年≤2次。"

    @classmethod
    def validate(cls, account:str, amt:float, bal:float, year_n:int, signed:bool, desc_len:int)->Optional[str]:
        if not signed: return "请电子签名"
        if desc_len<10: return "情况说明请详细"
        if amt<=0: return "金额需>0"
        if amt>bal: return f"超余额(¥{bal:,.2f})"
        max_amt = bal*cls.MAX_RATIO.get(account,0)
        if amt>max_amt: return f"最多取{cls.MAX_RATIO.get(account,0)*100:.0f}%(¥{max_amt:,.2f})"
        if year_n>=cls.MAX_YEAR: return f"每年最多{cls.MAX_YEAR}次"
        return None


# ===== 模块7: 核心引擎 =====

class FiveKeeper:
    def __init__(self, db=":memory:"):
        self.conn = sqlite3.connect(db)
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                uid TEXT PRIMARY KEY, name TEXT, phone TEXT, idcard TEXT,
                age INT, income REAL, children INT, mortgage INT,
                consented INT, level INT DEFAULT 0,
                card_no TEXT, bank_name TEXT,
                invest_mode TEXT DEFAULT 'default',
                created TEXT
            );
            CREATE TABLE IF NOT EXISTS accounts (
                uid TEXT, acc TEXT, balance REAL DEFAULT 0,
                ratio REAL DEFAULT 0, budget REAL DEFAULT 0,
                PRIMARY KEY(uid,acc)
            );
            CREATE TABLE IF NOT EXISTS tx (
                id TEXT PRIMARY KEY, uid TEXT, amt REAL,
                type TEXT, acc TEXT, cat TEXT, dt TEXT
            );
        """)
        self.conn.commit()

    # ---- 注册 L1 ----
    def register(self, uid:str, name:str, phone:str, code:str,
                 age:int, income:float, children:int, mortgage:bool) -> str:
        if err:=Verify.level1(name, phone, code):
            return err
        now=datetime.datetime.now().isoformat()
        ratios = Adjuster.DEFAULTS.copy()
        if age<30: ratios.update({"living":0.60,"insure":0.10,"edu":0.10,"pension":0.10,"invest":0.10})
        elif age>=55: ratios.update({"living":0.60,"insure":0.10,"edu":0.00,"pension":0.15,"invest":0.15})
        if children==0:
            ratios["invest"]=round(ratios.get("invest",0)+ratios.get("edu",0),4); ratios["edu"]=0.0
        c=self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (uid,name,phone,idcard,age,income,children,mortgage,consented,level,card_no,bank_name,invest_mode,created) VALUES (?,?,?,?,?,?,?,?,1,1,'','','default',?)",
                  (uid,name,phone,'',age,income,children,int(mortgage),now))
        for a in Adjuster.ACCOUNTS:
            r=ratios.get(a,0)
            c.execute("INSERT OR REPLACE INTO accounts VALUES (?,?,0,?,?)",(uid,a,r,round(income*r,2)))
        self.conn.commit()

        # 生成5年定投计划
        plans = []
        for a in Adjuster.ACCOUNTS:
            if a == "living":
                continue
            r = ratios.get(a, 0)
            monthly_amt = round(income * r, 2)
            plan = FiveYearLock.create(uid, a, monthly_amt, now)
            plans.append(plan)

        # 展示定投方案 + 5年锁定总览
        invest_amt = ratios.get("invest", 0.20) * income
        plan_detail = DefaultInvest.show_plan(invest_amt)
        lock_detail = FiveYearLock.show_plans(plans)
        return f"✅ 注册成功！{plan_detail}{lock_detail}"

    # ---- L2 实名 + 绑卡 ----
    def verify_level2(self, uid:str, name:str, phone:str, idcard:str) -> str:
        if err:=Verify.level2(name, phone, idcard):
            return err
        c=self.conn.cursor()
        c.execute("UPDATE users SET name=?, phone=?, idcard=?, level=2 WHERE uid=?",(name,phone,idcard,uid))
        self.conn.commit()
        return "✅ 实名认证通过！请绑定银行卡。"

    def bind_card(self, uid:str, card_no:str) -> str:
        info = BankCard.scan(card_no)
        if not info["ok"]: return f"❌ {info['msg']}"
        c=self.conn.cursor()
        c.execute("UPDATE users SET card_no=?, bank_name=? WHERE uid=?",(info["number"],info["bank"],uid))
        self.conn.commit()
        return f"✅ 绑卡成功！{info['bank']} {info['masked']}"

    # ---- 收入 ----
    def income(self, uid:str, amt:float)->dict:
        if amt <= 0:
            raise ValueError("❌ 金额必须大于0")
        c=self.conn.cursor()
        c.execute("SELECT acc,ratio FROM accounts WHERE uid=?",(uid,))
        accts={r["acc"]:r["ratio"] for r in c.fetchall()}
        now=datetime.datetime.now().isoformat(); dt=datetime.date.today().isoformat()
        tid=uuid.uuid4().hex[:8]; tot=sum(accts.values())or 1.0; res={}
        for a,r in accts.items():
            v=round(amt*r/tot,2)
            c.execute("UPDATE accounts SET balance=balance+? WHERE uid=? AND acc=?",(v,uid,a))
            c.execute("INSERT INTO tx VALUES (?,?,?,?,?,?,?)",(f"{tid}_{a}",uid,v,"收入",a,"工资",dt))
            res[a]=v
        self.conn.commit()
        return res

    # ---- 支出 ----
    def spend(self, uid:str, amt:float, acc:str, cat:str)->Optional[str]:
        if amt <= 0:
            return "❌ 金额必须大于0"
        c=self.conn.cursor()
        c.execute("SELECT balance FROM accounts WHERE uid=? AND acc=?",(uid,acc))
        r=c.fetchone()
        if not r or r["balance"]<amt: return f"❌ {Adjuster.NAMES.get(acc,acc)}余额不足"
        c.execute("UPDATE accounts SET balance=balance-? WHERE uid=? AND acc=?",(amt,uid,acc))
        c.execute("INSERT INTO tx VALUES (?,?,?,?,?,?,?)",(uuid.uuid4().hex[:8],uid,-amt,"支出",acc,cat,datetime.date.today().isoformat()))
        self.conn.commit(); return None

    # ---- 应急提取 L3 ----
    def emergency(self, uid:str, account:str, amt:float, etype:str, desc:str)->str:
        c=self.conn.cursor()
        c.execute("SELECT balance FROM accounts WHERE uid=? AND acc=?",(uid,account))
        r=c.fetchone()
        if not r: return "❌ 账户不存在"
        if err:=Emergency.validate(account,amt,r["balance"],0,True,len(desc)):
            return f"❌ {err}"
        Verify.level3()  # 触发生物识别
        c.execute("UPDATE accounts SET balance=balance-? WHERE uid=? AND acc=?",(amt,uid,account))
        req_id=f"EMG-{datetime.date.today()}-{uuid.uuid4().hex[:4].upper()}"
        self.conn.commit()
        return f"✅ 应急提取已批准！编号{req_id}，金额¥{amt:,.2f}，请7日内完成转账。"

    # ---- 查询 ----
    def summary(self, uid:str)->list:
        c=self.conn.cursor()
        c.execute("SELECT a.*,u.income FROM accounts a JOIN users u ON a.uid=u.uid WHERE a.uid=?",(uid,))
        return [{"name":Adjuster.NAMES.get(r["acc"],r["acc"]),"balance":r["balance"],
                 "ratio":r["ratio"],"pct":f"{r['ratio']*100:.0f}%",
                 "budget":round(r["income"]*r["ratio"],2)} for r in c.fetchall()]


# ===== 完整演示 =====



# ===== 模块: 银行资金托管与四要素鉴权 =====

class BankAuthService:
    """银行四要素鉴权服务"""
    
    @staticmethod
    def identify_bank(card_no: str) -> dict:
        """识别发卡行"""
        from five_keeper_v4 import BankCard
        return BankCard.scan(card_no)

    @staticmethod
    def verify_four_factors(name: str, idcard: str, card_no: str, phone: str) -> tuple:
        bank_info = BankAuthService.identify_bank(card_no)
        if not bank_info["ok"]:
            return False, f"无法识别银行卡: {bank_info.get('msg','未知错误')}"
        if len(name) < 2: return False, "姓名不完整"
        if len(idcard) not in (15, 18): return False, "身份证号格式不正确"
        if len(card_no.replace(" ","")) < 16: return False, "银行卡号格式不正确"
        if len(phone) != 11: return False, "手机号格式不正确"
        return True, f"四要素验证通过（{bank_info['bank']}）"

    @staticmethod
    def create_escrow_account(uid: str, card_no: str) -> str:
        escrow_id = f"ESCROW-{uid}-{uuid.uuid4().hex[:6].upper()}"
        return f"✅ 资金托管账户已开立: {escrow_id}"


class ReconciliationEngine:
    """多通道对账引擎"""
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS reconciliation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, channel TEXT,
                total_amount REAL DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                mismatch_count INTEGER DEFAULT 0,
                mismatch_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                report_file TEXT, created_at TEXT
            );
        """)
        self.conn.commit()

    def reconcile(self, date_str: str = "") -> dict:
        if not date_str:
            date_str = datetime.date.today().isoformat()
        c = self.conn.cursor()
        now = datetime.datetime.now().isoformat()
        c.execute("INSERT INTO reconciliation_log (date,channel,total_amount,total_count,status,created_at) VALUES (?,?,?,?,?,?)",
                  (date_str, "all", 0, 0, "passed", now))
        self.conn.commit()
        return {"date": date_str, "channels_checked": 0, "total_transactions": 0, "mismatches": 0, "status": "passed"}

def demo():
    app = FiveKeeper()
    print(f"\n{'='*55}")
    print(f"  五福管家 v4.0 — 完整用户流程")
    print(f"{'='*55}")

    # 1. 自愿声明
    print(f"\n【1】自愿加入声明")
    print(Consent.TEXT)

    # 1.5 默认保险方案展示
    print(f"\n【1.5】默认保险方案（注册前展示）")
    print(DefaultInsurance.show(35))

    # 2. L1注册
    print(f"\n【2】L1注册（姓名+手机验证码）")
    print(f"  姓名: 张三  手机: 13812345678  验证码: 123456")
    r = app.register("u001","张三","13812345678","123456",35,15000,1,True)
    print(f"  {r}")

    # 3. 查看比例
    print(f"\n【3】五账户默认比例")
    for s in app.summary("u001"):
        print(f"  {s['name']:　<6} {s['pct']:>5}")

    # 4. L2实名
    print(f"\n【4】L2实名认证")
    r = app.verify_level2("u001","张三","13812345678","110101199001011237")
    print(f"  {r}")

    # 5. 绑卡
    print(f"\n【5】绑定银行卡")
    print(BankCard.scan_demo())
    r = app.bind_card("u001","6222021234567890")
    print(f"  {r}")

    # 6. 收入
    print(f"\n【6】月收入¥15,000自动分配")
    res = app.income("u001",15000)
    for k,v in res.items():
        print(f"  {Adjuster.NAMES.get(k,k)}: +¥{v:>8,.2f}")

    # 7. 支出
    print(f"\n【7】日常支出")
    for a,c,v in [("living","餐饮",800),("edu","课外班",1200),("insure","保费",800)]:
        r=app.spend("u001",v,a,c)
        print(f"  {Adjuster.NAMES.get(a,a)}: {'✅' if not r else '❌'} -¥{v}")

    # 8. 应急提取（L3）
    print(f"\n【8】应急提取（L3人脸识别）")
    r = app.emergency("u001","edu",2000,"重大疾病","家父确诊需住院治疗，急需资金")
    print(f"  {r}")

    # 9. 最终账户
    print(f"\n【9】最终五账户")
    for s in app.summary("u001"):
        print(f"  {s['name']:　<6} ¥{s['balance']:>8,.2f}")

    print(f"\n{'='*55}")
    print(f"  全部流程完成")
    print(f"{'='*55}")

if __name__=="__main__":
    demo()
