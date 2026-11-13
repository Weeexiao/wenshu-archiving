"""Copy reviewed plan.csv; dry-run uses the same validation as execution."""
from pathlib import Path
import argparse,csv,datetime,shutil,sys,uuid
from archive_common import PERIODS,component,inside,source_files,sha
FIELDS=['期限','部门','序号','题名','源路径']
def execute(plan,root,dry_run=False,no_hyphen=False):
 root=Path(root).resolve()
 if not root.is_dir():raise ValueError('归档根目录不存在')
 with Path(plan).open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f)
  if not set(FIELDS)<=set(reader.fieldnames or []):raise ValueError('计划缺少必要表头')
  rows=[{k:(r.get(k) or '').strip() for k in FIELDS} for r in reader if any((v or '').strip() for v in r.values())]
 if not rows:raise ValueError('计划没有可执行记录')
 jobs={};destinations={};lines=[]
 for row in rows:
  period=component(row['期限']);dept=component(row['部门']);seq=row['序号'];title=component(row['题名'])
  if period not in PERIODS:raise ValueError('期限目录应为永久/长期/短期')
  if len(seq)!=4 or not seq.isascii() or not seq.isdigit() or seq=='0000':raise ValueError('序号须为0001~9999')
  source=Path(row['源路径']).expanduser().resolve()
  if inside(source,root) or inside(root,source):raise ValueError('源与归档根目录不能互相包含')
  target=(root/period/dept/(seq+('' if no_hyphen else '-')+title)).resolve()
  if not inside(target,root):raise ValueError('目标越过归档根目录')
  key=(period.casefold(),dept.casefold(),seq)
  if key in destinations and destinations[key]!=target:raise ValueError('同一期限部门序号对应多个题名')
  destinations[key]=target
  for src in source_files(source):
   relative=Path(src.name) if source.is_file() else src.relative_to(source)
   dst=(target/relative).resolve()
   if not inside(dst,target):raise ValueError('目标存在越界链接')
   collision=str(dst).casefold()
   if collision in jobs and sha(jobs[collision][0])!=sha(src):raise ValueError('计划中同名文件内容冲突：'+str(dst))
   if dst.exists() and (not dst.is_file() or sha(dst)!=sha(src)):raise ValueError('现有文件同名异内容，停止覆盖：'+str(dst))
   jobs[collision]=(src,dst)
 for src,dst in jobs.values():
  if dst.exists():lines.append('内容相同，跳过：'+str(dst));continue
  if dry_run:lines.append('拟复制：'+str(src)+' -> '+str(dst));continue
  dst.parent.mkdir(parents=True,exist_ok=True);temp=dst.with_name(dst.name+'.'+uuid.uuid4().hex+'.partial')
  try:
   shutil.copy2(src,temp)
   if sha(temp)!=sha(src):raise ValueError('复制后内容校验失败')
   try:
    # Exclusive creation: never overwrite an archive file created after preflight.
    with dst.open('xb') as out,temp.open('rb') as inp:shutil.copyfileobj(inp,out)
    shutil.copystat(temp,dst)
    if sha(dst)!=sha(temp):raise ValueError('目标内容校验失败')
   except FileExistsError:
    if not dst.is_file() or sha(dst)!=sha(temp):raise ValueError('复制期间目标被其他程序修改')
   lines.append('已复制并校验：'+str(dst))
  finally:
   if temp.exists():temp.unlink()
 return lines
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--root',required=True);p.add_argument('--log',default='');p.add_argument('--dry-run',action='store_true');p.add_argument('--no-hyphen',action='store_true');a=p.parse_args()
 try:lines=execute(a.plan,a.root,a.dry_run,a.no_hyphen);code=0
 except Exception as e:lines=['失败：'+str(e)];code=1
 print('\n'.join(lines))
 if a.log and not a.dry_run:
  log=Path(a.log);log.parent.mkdir(parents=True,exist_ok=True)
  with log.open('a',encoding='utf-8') as f:f.write(str(datetime.datetime.now())+'\n'+'\n'.join(lines)+'\n')
 return code
if __name__=='__main__':sys.exit(main())
