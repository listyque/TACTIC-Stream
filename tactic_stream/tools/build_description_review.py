"""Build the Description QML/browser comparison with the existing review viewer."""
from datetime import datetime, timezone
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '.screenshots/description-current'
states = ['empty','read','edit','pinned','process','snapshot','saving','error']
pairs = [dict(label=f'{state} · {width} px',handler=f'handler-{state}-{width}.png',stream=f'stream-{state}-{width}.png') for state in states for width in (440,720)]
for pair in pairs:
    for side in ('handler','stream'):
        if not (OUTPUT/pair[side]).is_file(): raise FileNotFoundError(pair[side])
manifest = dict(version='0.112.30',generatedAt=datetime.now(timezone.utc).isoformat(),pairs=pairs,
    sourceHashes=json.loads((OUTPUT/'native-source.json').read_text(encoding='utf-8')),
    fixtureNote='Current unchanged Handler QML/WorkspaceState and the rendered Chromium component, isolated at matching sizes. Working dock interactions/native updates are tested separately on private SQLite. No Handler connection.',
    checks=['repository-acceptance-final.log','description-final.log','working-panels-native.log'],
    boundaries=['Font rasterization differs; zero pixel difference is not claimed','Drafts stay in session memory; update uses native last-write-wins','Full Snapshot Browser/Drop Plate/Knowledge Base and the rest of point 3 remain unfinished'])
(OUTPUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
html = (ROOT/'.screenshots/configuration-current/index.html').read_text(encoding='utf-8')
html = re.sub(r'const pairs=.*?,screen=',lambda _: 'const pairs='+json.dumps(pairs,ensure_ascii=False).replace('<','\\u003c')+',screen=',html,count=1)
html = html.replace('Configuration','Description').replace('Восемь страниц и Repository Editor, два размера окна.','Восемь состояний редактора, два одинаковых размера.')
(OUTPUT/'index.html').write_text(html,encoding='utf-8')
print(f'{len(pairs)} fresh Description pairs: {OUTPUT / "index.html"}')
