"""Pair current offline Handler QML with rendered Chromium at matching sizes."""
from datetime import datetime, timezone
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '.screenshots/snapshot-browser-current'
states = ('empty','both','all','more','vertical','files','preview')
pairs = [dict(label=f'{state} · {width} px',handler=f'handler-{state}-{width}.png',stream=f'stream-{state}-{width}.png')
         for state in states for width in (440,880)]
for pair in pairs:
    for side in ('handler','stream'):
        if not (OUTPUT/pair[side]).is_file(): raise FileNotFoundError(pair[side])
manifest = dict(version='0.112.31',generatedAt=datetime.now(timezone.utc).isoformat(),pairs=pairs,
    sourceHashes=json.loads((OUTPUT/'native-source.json').read_text(encoding='utf-8')),
    fixtureNote='Current unchanged Handler QML + offline controller/models filled with a native-record fixture; rendered Chromium component at identical sizes. Native write/rollback and dock interactions tested separately. No Handler connection.',
    checks=['snapshot-browser-test.log','snapshot-browser-native.log','snapshot-browser-acceptance.log','snapshot-browser-regression.log','snapshot-browser-translations.log','snapshot-browser-build.log'],
    boundaries=['Qt/Chrome font rasterization differs; zero pixel difference is not claimed',
                'Individual metadata member rows for sequence/UDIM/UV groups remain pending',
                'Existing administrator workspace gate; ordinary-user and Qt-only image parity unverified',
                'Point 3 is in progress: Knowledge Base, Drop Plate/full Commit Queue and remaining working panels are not complete'])
(OUTPUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
html = (ROOT/'.screenshots/configuration-current/index.html').read_text(encoding='utf-8')
html = re.sub(r'const pairs=.*?,screen=',lambda _: 'const pairs='+json.dumps(pairs,ensure_ascii=False).replace('<','\\u003c')+',screen=',html,count=1)
html = html.replace('Configuration','Snapshot Browser').replace('Восемь страниц и Repository Editor, два размера окна.','Семь состояний браузера снапшотов при одинаковых размерах.')
html = re.sub(r'Stream 0\.112\.\d+','Stream 0.112.31',html)
(OUTPUT/'index.html').write_text(html,encoding='utf-8')
print(f'{len(pairs)} Snapshot Browser pairs: {OUTPUT / "index.html"}')
