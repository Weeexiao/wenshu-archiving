# -*- coding: utf-8 -*-
"""批量给归档单元文件夹改名：序号与题名之间加横杠（或反向去掉）。

    0053九建公司2025年发文登记簿  ->  0053-九建公司2025年发文登记簿

用法：
    python rename_units.py --root "Z:\\...\\2025年" --dry-run
    python rename_units.py --root "Z:\\...\\2025年"
    python rename_units.py --root "Z:\\...\\2025年" --dept 办公室 --dry-run
    python rename_units.py --root "..." --remove      # 反向：去掉横杠

只改「期限\\部门\\单元」这一层，单元内部的子文件夹不动。
已符合规则或命名不规范（不是 4 位数字开头）的自动跳过，可重复运行。
"""
import argparse
import datetime
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PERIODS = ["永久", "长期", "短期"]
PAT = re.compile(r"^(\d{4})-?(.+)$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--dept", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--remove", action="store_true", help="反向操作：去掉横杠")
    ap.add_argument("--log", default="")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("[错误] 目录不存在：%s" % root)
        return 2

    lines = []
    def say(m):
        print(m)
        lines.append(m)

    say("=" * 66)
    say("开始：%s  模式：%s  方向：%s" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "预览" if args.dry_run else "实际执行",
        "去掉横杠" if args.remove else "加横杠"))
    say("=" * 66)

    done = skip = fail = 0
    for period in PERIODS:
        pdir = os.path.join(root, period)
        if not os.path.isdir(pdir):
            continue
        say("")
        say("---------- %s ----------" % period)
        for dept in sorted(os.listdir(pdir)):
            ddir = os.path.join(pdir, dept)
            if not os.path.isdir(ddir):
                continue
            if args.dept and args.dept not in dept:
                continue
            cnt = 0
            for unit in sorted(os.listdir(ddir)):
                udir = os.path.join(ddir, unit)
                if not os.path.isdir(udir):
                    continue
                m = PAT.match(unit)
                if not m:
                    skip += 1
                    continue
                digits, rest = m.group(1), m.group(2)
                want = ("%s%s" % (digits, rest)) if args.remove else ("%s-%s" % (digits, rest))
                if want == unit:
                    skip += 1
                    continue
                target = os.path.join(ddir, want)
                if os.path.exists(target):
                    say("  [冲突跳过] %s" % unit)
                    skip += 1
                    continue
                if args.dry_run:
                    done += 1
                    cnt += 1
                    continue
                try:
                    os.rename(udir, target)
                    done += 1
                    cnt += 1
                except Exception as e:
                    say("  [失败] %s :: %s" % (unit, e))
                    fail += 1
            if cnt:
                say("  %s：%d 个" % (dept, cnt))

    say("")
    say("-" * 66)
    say("处理 %d 个；跳过 %d 个；失败 %d 个" % (done, skip, fail))
    if args.log and not args.dry_run:
        with open(args.log, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n" + "=" * 66 + "\n\n")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
