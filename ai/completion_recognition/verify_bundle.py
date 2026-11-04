"""Standard-library check: selected weights and policy are intact after unzip."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent/'model_bundle'
manifest=json.loads((root/'BUNDLE_MANIFEST.json').read_text(encoding='utf-8'))
for name,expected in manifest['files'].items():
    p=root/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise SystemExit('Corrupt or wrong model: '+name)
if hashlib.sha256((root/'POLICY_LOCK_BEFORE_TEST.json').read_bytes()).hexdigest()!=manifest['policy_lock_sha256']:
    raise SystemExit('Policy file changed')
print('BUNDLE OK: selected models and policy hashes match.')
