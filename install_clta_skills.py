#!/usr/bin/env python3
"""
邱数智方 · CLTA备课专业化技能安装器
====================================
安装前需验证密码，密码来自邱数智方董事会授权。

用法：
  python3 install_clta_skills.py
  （按提示输入密码）

密码验证通过后，自动安装到 Hermes Agent skills 目录。
"""

import os
import sys
import zipfile
import shutil
import getpass
import tempfile
from pathlib import Path

# ── 配置 ──────────────────────────────────────
PASSWORD = "d7538916"
SKILLS_ZIP = Path(__file__).parent / "clta-skills-encrypted.zip"
HERMES_SKILLS = Path.home() / "AppData" / "Local" / "hermes" / "skills"

# 技能列表
SKILLS = [
    "beike-zhuanyehua",
    "education-clta-math",
    "xuejiaoping-skill",
    "lesson-design-thinking",
]


def check_password() -> bool:
    pwd = getpass.getpass("请输入安装密码: ")
    return pwd == PASSWORD


def extract_and_install():
    if not SKILLS_ZIP.exists():
        print(f"❌ 未找到技能包: {SKILLS_ZIP}")
        print("请确保本脚本与 clta-skills-encrypted.zip 在同一目录")
        sys.exit(1)

    print(f"📦 正在解压技能包...")

    try:
        with zipfile.ZipFile(str(SKILLS_ZIP), 'r') as zf:
            zf.setpassword(PASSWORD.encode())
            for member in zf.namelist():
                if member.startswith('skills/'):
                    dest = os.path.join(str(HERMES_SKILLS), member[7:])
                else:
                    dest = os.path.join(str(HERMES_SKILLS), member)
                if member.endswith('/'):
                    os.makedirs(dest, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(member) as src, open(dest, 'wb') as dst:
                    dst.write(src.read())
    except RuntimeError as e:
        if "Bad password" in str(e) or "password" in str(e).lower():
            print("❌ 密码错误，安装终止")
            sys.exit(1)
        raise
    except Exception as e:
        print(f"❌ 解压失败: {e}")
        sys.exit(1)

    print(f"✅ 安装完成！")
    print(f"📂 安装路径: {HERMES_SKILLS}")
    print(f"\n已安装技能:")
    for skill in SKILLS:
        skill_path = HERMES_SKILLS / skill
        if skill_path.exists():
            print(f"  ✅ {skill}")
        else:
            print(f"  ⚠️  {skill} (未找到，请检查)")

    print(f"\n💡 技能加载方式:")
    print(f"  在 Hermes Agent 中加载对应话题即可自动激活")


def main():
    print("=" * 50)
    print("  邱数智方 · CLTA备课专业化技能安装器")
    print("  学教评一致性教学设计技能包")
    print("=" * 50)
    print()

    if not check_password():
        print("❌ 密码错误，安装终止")
        sys.exit(1)

    print("✅ 密码验证通过！")
    print()
    print(f"即将安装以下技能到 {HERMES_SKILLS}:")
    for s in SKILLS:
        print(f"  · {s}")
    print()

    confirm = input("是否继续安装？(Y/n): ").strip().lower()
    if confirm and confirm != 'y' and confirm != 'yes':
        print("安装已取消")
        sys.exit(0)

    extract_and_install()

    print()
    print("=" * 50)
    print("  安装完成！感谢使用邱数智方技能包")
    print("=" * 50)


if __name__ == "__main__":
    main()
