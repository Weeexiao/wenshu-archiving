# -*- coding: utf-8 -*-
"""盘点源目录，列出本年度可归档的候选材料。

用法：
    python scan_source.py --src "Z:\\办公室" --year 2025
    python scan_source.py --src "Z:\\办公室" --year 2025 --out 候选清单.md --depth 4
    python scan_source.py --src "Z:\\办公室" --src "D:\\我的资料\\2025" --year 2025   # 多源

输出：Markdown 表格，含相对路径、类型、文件数、修改时间、疑似混装夹标记。
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

SKIP_KEYWORDS = ["1  文书档案", "06.档案室", "08.档案管理", "$RECYCLE.BIN", "System Volume Information"]


def human(n):
    return datetime.datetime.fromtimestamp(n).strftime("%Y-%m-%d %H:%M")


def count_files(path):
    c = 0
    for _, _, files in os.walk(path):
        c += len(files)
    return c


def folder_year(dirpath, src):
    """从最近的祖先目录名里取年份（如 2025 / 04.2025年），没有则返回 None"""
    rel = os.path.relpath(dirpath, src)
    if rel == ".":
        return None
    parts = [p for p in rel.split(os.sep) if p not in (".", "")]
    for p in reversed(parts):
        m = re.search(r"(20\d{2})", p)
        if m:
            return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, nargs="+",
                    help="一个或多个源目录；资料分散时把每个位置都传进来")
    ap.add_argument("--year", default=str(datetime.date.today().year))
    ap.add_argument("--depth", type=int, default=6)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    srcs = [os.path.abspath(s) for s in args.src]
    for s in srcs:
        if not os.path.isdir(s):
            print("[错误] 源目录不存在：%s" % s)
            return 2

    all_rows = []
    for src in srcs:
        all_rows.extend(scan_one(src, args.year, args.depth))

    rows = all_rows
    if not rows:
        print("未找到 %s 年的候选材料。" % args.year)
        return 0

    if len(srcs) == 1:
        head = "# %s 年候选材料清单（源：%s）" % (args.year, srcs[0])
    else:
        head = "# %s 年候选材料清单（%d 个源目录）\n\n" % (args.year, len(srcs))
        head += "\n".join("- %s" % s for s in srcs)
    lines = [head, "",
             "共 %d 项。归档前请逐项确认：是否本年度、是否已在目录中、归哪个期限。" % len(rows), "",
             "| # | 源 | 相对路径 | 类型 | 文件数 | 修改时间 | 备注 |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(sorted(rows, key=lambda x: (x["src"], x["path"])), 1):
        lines.append("| %d | %s | %s | %s | %d | %s | %s |" % (
            i, os.path.basename(r["src"]), r["path"], r["kind"], r["count"], r["mtime"], r["flag"]))

    text = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("已写出：%s（%d 项，%d 个源目录）" % (args.out, len(rows), len(srcs)))
    else:
        print(text)
    return 0


def scan_one(src, year, depth):
    """扫描单个源目录，返回候选行列表。"""
    rows = []
    for dirpath, dirnames, filenames in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        d = 0 if rel == "." else rel.count(os.sep) + 1
        # 跳过档案成果目录
        if any(k in dirpath for k in SKIP_KEYWORDS):
            dirnames[:] = []
            continue
        if d > depth:
            dirnames[:] = []
            continue

        # 判断当前目录属于哪个年度（取最近一层带年份的目录名）
        fy = folder_year(dirpath, src)
        if fy is not None and fy != year:
            dirnames[:] = [] if d >= 1 else dirnames
            continue

        # 文件级候选
        for fn in filenames:
            if fn.startswith("~$") or fn.startswith("."):
                continue
            if fy != year and year not in fn:
                continue
            fp = os.path.join(dirpath, fn)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            rows.append({
                "src": src,
                "path": os.path.relpath(fp, src),
                "kind": "文件",
                "count": 1,
                "mtime": human(st.st_mtime),
                "size": st.st_size,
                "flag": "",
            })

        # 识别"混装夹"：同级里其他目录都带数字前缀、它不带
        if dirnames:
            siblings = dirnames
            prefixed = [x for x in siblings if x[:1].isdigit()]
            if len(prefixed) >= 3:
                for x in siblings:
                    if not x[:1].isdigit():
                        rows.append({
                            "src": src,
                            "path": os.path.relpath(os.path.join(dirpath, x), src),
                            "kind": "目录",
                            "count": count_files(os.path.join(dirpath, x)),
                            "mtime": human(os.path.getmtime(os.path.join(dirpath, x))),
                            "size": 0,
                            "flag": "⚠ 混装夹（同级都有编号，它没有）",
                        })
    return rows


if __name__ == "__main__":
    sys.exit(main())
