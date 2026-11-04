"""Restore allowlisted, hash-verified experiment data without overwriting code."""
import argparse,hashlib,json,os,tempfile,zipfile
from pathlib import Path,PurePosixPath

def restore(archive,experiment):
 root=Path(experiment).resolve();lock=json.loads((root/'input_hashes.json').read_text(encoding='utf-8'))
 allowed_suffixes={'.json','.npz','.jpg','.jpeg','.png'};prepared=[]
 with zipfile.ZipFile(archive) as z:
  names={}
  for item in z.infolist():
   key=item.filename.replace('\\','/')
   if key in names:raise ValueError('Duplicate archive entry: '+key)
   names[key]=item
  # Verify all entries before writing any target data.
  for name,expected in lock.items():
   part=PurePosixPath(name)
   if part.is_absolute() or '..' in part.parts or '\\' in name or ':' in name or part.suffix.lower() not in allowed_suffixes:raise ValueError('Unsafe data path: '+name)
   target=root.joinpath(*part.parts)
   if not target.resolve().is_relative_to(root):raise ValueError('Data path escapes experiment')
   matches=[name] if name in names else [k for k in names if k.endswith('/'+name)]
   if len(matches)!=1:raise ValueError('Missing or ambiguous archive data: '+name)
   info=names[matches[0]]
   if info.file_size>64*1024*1024:raise ValueError('Unexpected data size: '+name)
   h=hashlib.sha256()
   with z.open(info) as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
   if h.hexdigest()!=expected:raise ValueError('Data hash mismatch: '+name)
   prepared.append((info,target))
  for info,target in prepared:
   target.parent.mkdir(parents=True,exist_ok=True)
   with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as dst:
    temp=Path(dst.name)
    try:
     with z.open(info) as src:
      for chunk in iter(lambda:src.read(1024*1024),b''):dst.write(chunk)
    except BaseException:temp.unlink(missing_ok=True);raise
   try:os.replace(temp,target)
   finally:temp.unlink(missing_ok=True)
 print(f'RESTORE OK: {len(prepared)} hash-verified data files. No server code or model weights changed.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',required=True);p.add_argument('--experiment',required=True);a=p.parse_args();restore(a.archive,a.experiment)
