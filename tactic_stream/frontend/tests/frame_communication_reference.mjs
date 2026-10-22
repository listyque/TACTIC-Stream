import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const reference = JSON.parse(
  readFileSync(root + 'tools/frame_messages/output/native.json', 'utf8')
);
for (const [prefix, sources] of [
  [root + 'src/tactic_stream/shared_ui/', reference.shared],
  ['D:/grav/Tactic Stream/TH/', reference.nativeSources],
  [root, reference.driverSources]
]) {
  for (const [name, hash] of Object.entries(sources)) {
    assert.equal(
      createHash('sha256')
        .update(readFileSync(prefix + name))
        .digest('hex'),
      hash,
      'Stale communication reference; rerun tools/frame_messages/capture.py: ' +
        name
    );
  }
}

export function nativeCases(screen) {
  const rows = reference.captures.filter(
    (row) =>
      !row.original &&
      row.fixture.screen === screen &&
      row.fixture.style === 'md3' &&
      row.fixture.language === 'en' &&
      row.fixture.dark
  );
  assert(rows.length, 'Missing native communication cases: ' + screen);
  return rows;
}
