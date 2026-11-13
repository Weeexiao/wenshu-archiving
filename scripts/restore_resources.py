"""Restore the template from a text resource, without changing existing files."""
from pathlib import Path
import base64,hashlib,json
ROOT=Path(__file__).resolve().parent.parent
def restore():
 resources=json.loads((ROOT/'assets/template-resource.json').read_text('utf-8'))
 for name,item in resources.items():
  target=(ROOT/name).resolve()
  if not target.is_relative_to(ROOT):raise ValueError('资源路径越界')
  data=base64.b64decode(item['base64'],validate=True)
  if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('内置模板校验失败')
  if target.exists():
   if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('现有模板已修改，保留并核对，不覆盖')
   continue
  target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.restore');temp.write_bytes(data);temp.replace(target)
 print('模板已就绪')
if __name__=='__main__':restore()
