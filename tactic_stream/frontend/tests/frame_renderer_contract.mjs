import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { controlKinds } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

assert(process.argv[2], 'Pass the independent Handler checkout path');
const native = await readFile(
  path.join(process.argv[2], 'thlib/ui/qml/tactic_frame/core/FrameView.qml'),
  'utf8'
);
const browser = await readFile(
  new URL('../src/frame/FrameView.vue', import.meta.url),
  'utf8'
);
const nativeKinds = new Set(
  [...native.matchAll(/case\s+"(\w+)"\s*:/g)].map((match) => match[1])
);
const browserKinds = new Set(
  [...browser.matchAll(/node\.kind\s*===\s*'(\w+)'/g)].map((match) => match[1])
);
assert.deepEqual([...nativeKinds].sort(), [...controlKinds].sort());
assert.deepEqual([...browserKinds].sort(), [...controlKinds].sort());
console.log(
  controlKinds.length,
  'Frame kinds have explicit registrations in both renderers; real input is checked by the platform and Administration suites.'
);
