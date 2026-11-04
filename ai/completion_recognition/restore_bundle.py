"""Restore four selected model binaries from a local V50 handoff ZIP; no download."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,shutil,tempfile,zipfile

ROOT=Path(__file__).resolve().parent
def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def restore(archive,root=ROOT):
    bundle=Path(root)/'model_bundle'
    manifest=json.loads((bundle/'BUNDLE_MANIFEST.json').read_text(encoding='utf-8'))
    expected=manifest['files']
    if set(expected)!={'encoder_supcon.pt','temporal_final.pt','stage_prototypes.pt','rider_verifier.npz'}:
        raise ValueError('Unexpected model manifest')
    if file_sha(bundle/'POLICY_LOCK_BEFORE_TEST.json')!=manifest['policy_lock_sha256']:
        raise ValueError('Policy metadata changed')
    # Stage and verify all assets before installing any missing model.
    with zipfile.ZipFile(archive) as z,tempfile.TemporaryDirectory(dir=bundle,prefix='restore_') as tmp:
        for name,digest in expected.items():
            suffix='model_bundle/'+name;found=[]
            for info in z.infolist():
                normalized=info.filename.replace('\\','/');parts=PurePosixPath(normalized)
                if parts.is_absolute() or '..' in parts.parts:continue
                if normalized==suffix or normalized.endswith('/'+suffix):found.append(info)
            if len(found)!=1:raise ValueError(f'Expected one {suffix}, found {len(found)}')
            staged=Path(tmp)/name
            with z.open(found[0]) as src,staged.open('wb') as dst:shutil.copyfileobj(src,dst,1024*1024)
            if file_sha(staged)!=digest:raise ValueError('Wrong or corrupt model: '+name)
            target=bundle/name
            if target.exists() and file_sha(target)!=digest:
                raise ValueError('Existing model differs; preserve/rename it before restoring: '+name)
        for name in expected:
            if not (bundle/name).exists():os.replace(Path(tmp)/name,bundle/name)
    print('RESTORE OK: four selected model files verified. No training required.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--zip',type=Path,required=True)
    a=p.parse_args();restore(a.zip)
if __name__=='__main__':main()
