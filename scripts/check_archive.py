# -*- coding: utf-8 -*-
"""归档成果自检：单元数对账、空单元、同名单元、命名格式。

用法：
    python check_archive.py --root "Z:\\...\\1  文书档案\\2025年"
    python check_archive.py --root "..." --catalog "附件3：九建公司2025年管理类档案目录.xlsx"
    python check_archive.py --root "..." --dept 办公室    # 只看某个部门

只读，不修改任何文件。有 catalog 时会与目录表统计行、档号数量对照。
"""
import argparse
import os
import re
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PERIODS = ["永久", "长期", "短期"]
UNIT_PAT = re.compile(r"^(\d{4})-?(.+)$")


def scan_units(root, dept_filter=None):
    """返回 [(期限, 部门, 单元名, 路径, 文件数)]"""
    out = []
    for period in PERIODS:
        pdir = os.path.join(root, period)
        if not os.path.isdir(pdir):
            continue
        for dept in sorted(os.listdir(pdir)):
            ddir = os.path.join(pdir, dept)
            if not os.path.isdir(ddir):
                continue
            if dept_filter and dept_filter not in dept:
                continue
            for unit in sorted(os.listdir(ddir)):
                udir = os.path.join(ddir, unit)
                if not os.path.isdir(udir):
                    continue
                n = 0
                for _, _, files in os.walk(udir):
                    n += len(files)
                out.append((period, dept, unit, udir, n))
    return out


def catalog_stats(path):
    """返回 {期限: (单元数, 记录数)}，从统计行解析"""
    try:
        import openpyxl
    except ImportError:
        return None
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        print("  [警告] 打不开目录表：%s" % e)
        return None
    stats = {}
    for ws in wb.worksheets:
        v = ws.cell(2, 1).value
        m = re.search(r"共\s*(\d+)\s*个归档单元[、,]\s*(\d+)\s*条文件记录", str(v or ""))
        if m:
            stats[ws.title] = (int(m.group(1)), int(m.group(2)))
    try:
        wb.close()
    except Exception:
        pass
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--catalog", default="")
    ap.add_argument("--dept", default="")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("[错误] 目录不存在：%s" % root)
        return 2

    units = scan_units(root, args.dept or None)
    print("=" * 66)
    print("归档自检：%s" % root)
    print("=" * 66)

    by_period = defaultdict(list)
    for u in units:
        by_period[u[0]].append(u)

    problems = []

    # 1. 单元数 / 空单元 / 命名
    print("\n【一】数量与命名")
    for period in PERIODS:
        us = by_period.get(period, [])
        if not us:
            continue
        empty = [u for u in us if u[4] == 0]
        bad = [u for u in us if not UNIT_PAT.match(u[2])]
        nohyphen = [u for u in us if UNIT_PAT.match(u[2]) and not re.match(r"^\d{4}-", u[2])]
        print("  %s：%d 个单元，空单元 %d，命名异常 %d，未加横杠 %d"
              % (period, len(us), len(empty), len(bad), len(nohyphen)))
        for u in empty:
            problems.append("[空单元] %s\\%s\\%s" % (period, u[1], u[2]))
        for u in bad:
            problems.append("[命名异常] %s\\%s\\%s" % (period, u[1], u[2]))

    # 2. 同名单元（同期限同部门内）
    print("\n【二】同名单元（同期限、同部门题名重复）")
    print("  提示：同名不一定是重复。同名但文号/日期不同的，可能是不同批次的同类请示，需人工判断。")
    dup_found = False
    for period in PERIODS:
        seen = defaultdict(list)
        for u in by_period.get(period, []):
            m = UNIT_PAT.match(u[2])
            title = m.group(2) if m else u[2]
            seen[(u[1], title)].append(u[2])
        for (dept, title), names in seen.items():
            if len(names) > 1:
                dup_found = True
                print("  %s / %s：%s" % (period, dept, " | ".join(names)))
                problems.append("[同名单元] %s\\%s\\%s" % (period, dept, " / ".join(names)))
    if not dup_found:
        print("  无")

    # 3. 与目录表对账
    if args.catalog and args.dept:
        print("\n【三】与目录表对账：已按 --dept 过滤，跳过全表对账（避免数字误报）")
    elif args.catalog:
        print("\n【三】与目录表对账：%s" % os.path.basename(args.catalog))
        stats = catalog_stats(args.catalog)
        if not stats:
            print("  [跳过] 需要 openpyxl，或文件被占用")
        else:
            for period in PERIODS:
                us = by_period.get(period, [])
                if not us:
                    continue
                cat = stats.get(period)
                if not cat:
                    print("  %s：目录表未找到统计行" % period)
                    continue
                flag = "OK" if cat[0] == len(us) else "不一致"
                print("  %s：实体 %d 个单元 / 目录 %d 个单元  -> %s" % (period, len(us), cat[0], flag))
                if cat[0] != len(us):
                    problems.append("[数量不一致] %s：实体 %d ≠ 目录 %d" % (period, len(us), cat[0]))

    print("\n" + "-" * 66)
    if problems:
        print("发现 %d 处需要处理：" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("未发现问题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
