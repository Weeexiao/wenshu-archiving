"""Shared local path and content checks. No network operations."""
from pathlib import Path
import hashlib,re
PERIODS=['永久','长期','短期']
UNIT=re.compile(r'^(\d{4})(?!\d)-?(.+)$')
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inside(path,root):return Path(path).resolve().is_relative_to(Path(root).resolve())
def component(value):
 value=str(value).strip()
 if not value or value in {'.','..'} or re.search(r'[\\/:*?"<>|\x00-\x1f]',value) or value.endswith(('.', ' ')):raise ValueError('非法路径字段：'+value)
 if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',value):raise ValueError('保留文件名：'+value)
 return value
def source_files(source):
 source=Path(source).resolve()
 if source.is_file():files=[source]
 elif source.is_dir():
  candidates=list(source.rglob('*'))
  if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in candidates):raise ValueError('源资料含链接目录或文件，请单独核对')
  files=[p for p in candidates if p.is_file()]
 else:raise ValueError('源不存在：'+str(source))
 if not files or not any(p.stat().st_size>0 for p in files):raise ValueError('源为空或只有零字节文件：'+str(source))
 return sorted(files)
