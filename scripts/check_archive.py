"""Read-only reconciliation of actual archive units and catalog rows."""
from pathlib import Path
import argparse,re,sys
from collections import defaultdict
from archive_common import PERIODS,UNIT,source_files
def scan_units(root,dept_filter=None):
 out=[]
 for period in PERIODS:
  p=Path(root)/period
  if not p.is_dir():continue
  for dept in sorted(p.iterdir()):
   if not dept.is_dir() or (dept_filter and dept_filter not in dept.name):continue
   for unit in sorted(dept.iterdir()):
    if not unit.is_dir():continue
    files=[f for f in unit.rglob('*') if f.is_file() and not f.name.endswith('.partial')]
    out.append((period,dept.name,unit.name,str(unit),sum(f.stat().st_size>0 for f in files)))
 return out
def inspect(root,catalog=None,dept_filter=None):
 units=scan_units(root,dept_filter);problems=[];actual={};titles=defaultdict(list)
 for period,dept,name,path,count in units:
  m=UNIT.fullmatch(name)
  if not count:problems.append('空单元或只有零字节文件：'+path)
  if not m or m[1]=='0000':problems.append('单元命名异常：'+path);continue
  key=(period,dept,m[1]);titles[(period,dept,m[2])].append(name)
  if key in actual:problems.append('同一期限部门序号重复：'+path)
  actual[key]=name
  if not re.match(r'^\d{4}-',name):problems.append('序号与题名之间缺横杠：'+path)
  if any(p.name.endswith('.partial') for p in Path(path).rglob('*')):problems.append('复制残留临时文件：'+path)
 for key,names in titles.items():
  if len(names)>1:problems.append('同名待核对（不能仅凭同名删除）：'+str(key)+' '+str(names))
 if catalog:
  try:import openpyxl
  except ImportError:raise RuntimeError('指定目录对账需要openpyxl，不能跳过后宣称通过')
  wb=openpyxl.load_workbook(catalog,read_only=True,data_only=True);expected=set()
  try:
   for period in PERIODS:
    if period not in wb.sheetnames:raise ValueError('目录缺表：'+period)
    sheet=wb[period];allcodes=set();records=0
    for row in sheet.iter_rows(min_row=4,max_col=10,values_only=True):
     if not any(v is not None for v in row):continue
     seq,code,_,_,creator,title,date,retention,dept,notes=row
     if not code:problems.append('目录记录缺档号：'+period+' '+str(title));continue
     records+=1;allcodes.add(str(code))
     if not dept or not title or not creator or not date:problems.append('目录必填项缺失：'+str(code))
     if retention!={'永久':'永久','长期':'30年','短期':'10年'}[period]:problems.append('期限与分表不符：'+str(code))
     if dept_filter and dept_filter not in str(dept):continue
     match=re.fullmatch(r'.+-GL-(20\d{2})-(Y|D30|D10)-([A-Za-z0-9]+)-(\d{4})',str(code))
     if not match:problems.append('档号格式异常：'+str(code));continue
     if match[2]!={'永久':'Y','长期':'D30','短期':'D10'}[period]:problems.append('档号期限码与分表不符：'+str(code))
     expected.add((period,str(dept),match[4]))
    m=re.search(r'共\s*(\d+)\s*个归档单元[、,，]\s*(\d+)\s*条文件记录',str(sheet.cell(2,1).value or ''))
    if not m or (int(m[1]),int(m[2]))!=(len(allcodes),records):problems.append('统计行与实际记录不符：'+period)
   for k in sorted(expected-set(actual)):problems.append('目录有、实体缺：'+str(k))
   for k in sorted(set(actual)-expected):problems.append('实体有、目录缺：'+str(k))
  finally:wb.close()
 return units,problems
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--catalog');p.add_argument('--dept',default='');a=p.parse_args()
 if not Path(a.root).is_dir():print('根目录不存在');return 2
 try:units,issues=inspect(a.root,a.catalog,a.dept or None)
 except Exception as e:print('自检未完成：'+str(e));return 2
 print('已检查实体单元：'+str(len(units)))
 print('\n'.join(issues) if issues else '本次已执行检查通过'+('。' if a.catalog else '；未提供目录表，尚未进行目录对账。'))
 return 1 if issues else 0
if __name__=='__main__':sys.exit(main())
