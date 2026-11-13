"""Filesystem regressions; all work is confined to temporary directories."""
from pathlib import Path
import csv,subprocess,sys,tempfile,unittest
S=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(S/'scripts'))
from copy_units import execute,FIELDS
from scan_source import scan_one
from check_archive import inspect
class Workflows(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.b=Path(self.temp.name);self.root=self.b/'archive';self.root.mkdir();self.src=self.b/'source';self.src.mkdir();(self.src/'a.txt').write_text('alpha');self.plan=self.b/'plan.csv'
 def plan_rows(self,rows=None):
  rows=rows or [['永久','办公室','0001','测试',str(self.src/'a.txt')]]
  with self.plan.open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(FIELDS);w.writerows(rows)
  return self.plan
 def test_dryrun_and_resume(self):
  self.plan_rows();execute(self.plan,self.root,True);self.assertFalse(list(self.root.iterdir()));execute(self.plan,self.root);execute(self.plan,self.root);self.assertEqual((self.root/'永久/办公室/0001-测试/a.txt').read_text(),'alpha')
 def test_same_name_different_content_blocks_entire_batch(self):
  self.plan_rows();execute(self.plan,self.root);(self.src/'a.txt').write_text('revision');self.plan_rows([['永久','办公室','0002','新增',str(self.src/'a.txt')],['永久','办公室','0001','测试',str(self.src/'a.txt')]])
  with self.assertRaises(ValueError):execute(self.plan,self.root)
  self.assertFalse((self.root/'永久/办公室/0002-新增').exists());self.assertEqual((self.root/'永久/办公室/0001-测试/a.txt').read_text(),'alpha')
 def test_empty_source_rejected(self):
  empty=self.b/'empty';empty.mkdir();(empty/'zero').touch();self.plan_rows([['长期','办公室','0001','空',str(empty)]])
  with self.assertRaises(ValueError):execute(self.plan,self.root)
  self.assertFalse(list(self.root.iterdir()))
 def test_path_traversal_rejected(self):
  self.plan_rows([['永久','../外部','0001','测试',str(self.src)]])
  with self.assertRaises(ValueError):execute(self.plan,self.root)
 def test_nested_input_output_rejected(self):
  inner=self.src/'results';inner.mkdir();self.plan_rows([['永久','办公室','0001','测试',str(self.src)]])
  with self.assertRaises(ValueError):execute(self.plan,inner)
 def test_duplicate_sequence_rejected(self):
  self.plan_rows([['永久','办公室','0001','甲',str(self.src)],['永久','办公室','0001','乙',str(self.src)]])
  with self.assertRaises(ValueError):execute(self.plan,self.root)
 def test_unnamed_year_and_other_year_not_lost(self):
  old=self.src/'2025';old.mkdir();(old/'无年份.docx').write_text('x');rows=scan_one(str(self.src),'2026',6);self.assertEqual(len(rows),2);self.assertTrue(all('待核对' in r['flag'] for r in rows))
 def test_repeated_src_arguments(self):
  other=self.b/'other';other.mkdir();(other/'b.txt').write_text('beta');report=self.b/'report.md'
  subprocess.run([sys.executable,str(S/'scripts/scan_source.py'),'--src',str(self.src),'--src',str(other),'--year','2026','--out',str(report)],check=True,capture_output=True)
  t=report.read_text('utf-8');self.assertIn('a.txt',t);self.assertIn('b.txt',t)
 def test_output_excluded(self):
  results=self.src/'results';results.mkdir();(results/'old.txt').write_text('old');rows=scan_one(str(self.src),'2026',6,[str(results)]);self.assertEqual(len(rows),1)
 def test_empty_unit_and_duplicate_number_detected(self):
  for name in ['0001-甲','0001-乙']:(self.root/'永久/办公室'/name).mkdir(parents=True)
  _,issues=inspect(self.root);self.assertTrue(any('空单元' in x for x in issues));self.assertTrue(any('序号重复' in x for x in issues))
 def make_catalog(self):
  import openpyxl
  wb=openpyxl.Workbook();wb.remove(wb.active)
  for period in ['永久','长期','短期']:
   ws=wb.create_sheet(period);ws.append(['标题']);ws.append(['共 0 个归档单元、0 条文件记录，按归档机构和档号排序']);ws.append(['序号','档号','收发文','文号','责任者','题名','日期','保管期限','归档机构','备注'])
  ws=wb['永久'];ws.cell(2,1,'共 1 个归档单元、1 条文件记录，按归档机构和档号排序')
  import datetime
  ws.append([1,'SIGJ09-GL-2026-Y-BGS-0001',None,None,'单位甲','测试',datetime.datetime(2026,1,1),'永久','办公室',None]);p=self.b/'catalog.xlsx';wb.save(p);return p
 def test_catalog_missing_all_entities_detected(self):
  _,issues=inspect(self.root,self.make_catalog());self.assertTrue(any('实体缺' in x for x in issues))
 def test_catalog_entity_matching(self):
  self.plan_rows();execute(self.plan,self.root);_,issues=inspect(self.root,self.make_catalog());self.assertEqual(issues,[])
 def test_catalog_no_same_count_false_positive(self):
  self.plan_rows([['永久','办公室','0002','测试',str(self.src/'a.txt')]]);execute(self.plan,self.root);_,issues=inspect(self.root,self.make_catalog());self.assertTrue(any('实体缺' in x for x in issues));self.assertTrue(any('目录缺' in x for x in issues))
 def test_rename_collision_returns_failure(self):
  for name in ['0001测试','0001-测试']:(self.root/'永久/办公室'/name).mkdir(parents=True)
  p=subprocess.run([sys.executable,str(S/'scripts/rename_units.py'),'--root',str(self.root),'--dry-run'],capture_output=True);self.assertEqual(p.returncode,1)
if __name__=='__main__':unittest.main()
