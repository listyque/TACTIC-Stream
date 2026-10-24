import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Load the resolver and real charmaps without requiring a browser or Vite.
const source = readFileSync(
  new URL('../src/icons.js', import.meta.url),
  'utf8'
);
const code = source
  .replace(
    "'../../src/tactic_stream/shared_ui/core/icons.mjs'",
    JSON.stringify(
      new URL(
        '../../src/tactic_stream/shared_ui/core/icons.mjs',
        import.meta.url
      ).href
    )
  )
  .replace(
    /^import (\w+) from '([^']+)'/gm,
    (_, name, path) =>
      `const ${name} = ${readFileSync(new URL('../src/' + path, import.meta.url), 'utf8')}`
  );
const { resolveIcon, iconMaps } = await import(
  'data:text/javascript;base64,' + Buffer.from(code).toString('base64')
);
const { legacyIcons } = await import(
  '../../src/tactic_stream/shared_ui/core/legacy_icons.mjs'
);
const templateIcons = JSON.parse(
  readFileSync(
    new URL('../../tests/fixtures/legacy_template_icons.json', import.meta.url),
    'utf8'
  )
);
for (const pack of Object.keys(iconMaps)) {
  for (const name of templateIcons)
    assert(
      resolveIcon(name, pack),
      `Legacy template ${name} must resolve in ${pack}`
    );
  for (const [name, [semantic, source]] of Object.entries(legacyIcons)) {
    const expected = resolveIcon(semantic, pack);
    assert(expected, `${name} replacement must exist in ${pack}`);
    const file = source.slice(source.lastIndexOf('/') + 1);
    const references = [name, source, file, file.replace(/\.[^.]+$/, '')];
    if (!source.startsWith('/'))
      references.push('/context/icons/silk/' + source);
    for (const reference of references)
      assert.deepEqual(
        resolveIcon(reference, pack),
        expected,
        reference + ':' + pack
      );
  }
  assert.deepEqual(
    resolveIcon('BS_LIST_ALT', pack),
    resolveIcon('view-list', pack)
  );
  assert.deepEqual(
    resolveIcon('Contents', pack),
    resolveIcon('view-list', pack)
  );
  assert.deepEqual(
    resolveIcon('FAS_TELEVISION', pack),
    resolveIcon('fontawesome-solid:tv', pack)
  );
  for (const name of [
    'https://custom.invalid/film.png',
    '/custom/film.png',
    'CUSTOM_PROJECT_ICON'
  ])
    assert.equal(resolveIcon(name, pack), undefined);
}
if (process.argv[2])
  for (const name of [
    'materialdesignicons-webfont.ttf',
    'fontawesome5-solid-webfont.ttf',
    'fontawesome5-regular-webfont.ttf',
    'fluent-system-icons-resizable.ttf'
  ])
    assert.deepEqual(
      readFileSync(new URL('../src/assets/fonts/' + name, import.meta.url)),
      readFileSync(process.argv[2] + '/thlib/ui/assets/fonts/' + name),
      'Both native renderers must use the same font bytes: ' + name
    );
for (const [family, map] of Object.entries(iconMaps)) {
  const name = Object.keys(map)[0],
    value = map[name];
  assert.deepEqual(resolveIcon(family + ':' + name, 'automatic'), [
    family,
    String.fromCodePoint(
      typeof value === 'number' ? value : parseInt(value, 16)
    )
  ]);
}
assert.deepEqual(
  resolveIcon('FAS_PLAY', 'material-design'),
  resolveIcon('fontawesome-solid:play', 'material-design')
);
assert.deepEqual(
  resolveIcon('MDI_PLAY', 'fontawesome-solid'),
  resolveIcon('material-design:play', 'fontawesome-solid')
);
assert.deepEqual(
  resolveIcon('play-arrow', 'material-design'),
  resolveIcon('material-design:play', 'material-design')
);
assert.equal(resolveIcon('unknown:play', 'fontawesome-solid'), undefined);
assert.equal(
  resolveIcon('fontawesome-solid:missing-icon', 'material-design'),
  undefined
);
assert.equal(resolveIcon('', 'material-design'), undefined);
for (const pack of Object.keys(iconMaps))
  for (const [name, canonical] of [
    ['more', 'more_vert'],
    ['connection', 'lan-connect']
  ])
    assert.deepEqual(resolveIcon(name, pack), resolveIcon(canonical, pack));
for (const pack of Object.keys(iconMaps))
  for (const name of [
    'schedule',
    'history',
    'person',
    'process',
    'status',
    'sobject',
    'schema',
    'workspaces',
    'priority-high',
    'milestone',
    'admin-panel-settings',
    'ungroup-items'
  ])
    assert(resolveIcon(name, pack), pack + ':' + name);
for (const pack of Object.keys(iconMaps))
  for (const name of [
    'dns',
    'desktop',
    'delete-sweep',
    'priority-high',
    'warning',
    'info',
    'notifications',
    'activity-feed',
    'dynamic-feed',
    'sync',
    'check-circle',
    'task',
    'notes',
    'snapshot',
    'select-all',
    'inventory-2',
    'system-activity',
    'schedule',
    'groups',
    'open-in-full',
    'window-restore'
  ])
    assert(resolveIcon(name, pack), pack + ':' + name);
console.log('PASS all five native set:name icon catalogs and legacy aliases');
for (const pack of Object.keys(iconMaps)) {
  const name = pack.startsWith('fluent-')
    ? 'text-description'
    : pack === 'material-design'
      ? 'text-box'
      : 'file-alt';
  const family = iconMaps[pack][name] ? pack : 'fontawesome-solid';
  assert.deepEqual(
    resolveIcon('description', pack),
    resolveIcon(family + ':' + name, pack)
  );
}
for (const pack of Object.keys(iconMaps))
  for (const name of [
    'tab',
    'activity',
    'queue',
    'appearance',
    'fact-check',
    'text-fields'
  ])
    assert(resolveIcon(name, pack), pack + ':' + name);
for (const pack of Object.keys(iconMaps)) {
  const family = pack === 'fontawesome-outline' ? 'fontawesome-solid' : pack;
  const name = pack.startsWith('fluent-')
    ? 'cloud-arrow-up'
    : pack === 'material-design'
      ? 'cloud-upload'
      : 'cloud-upload-alt';
  assert.deepEqual(
    resolveIcon('commit-queue', pack),
    resolveIcon(family + ':' + name, pack)
  );
}

for (const pack of Object.keys(iconMaps))
  for (const name of ['book-open', 'file', 'person-add'])
    assert(resolveIcon(name, pack), pack + ':' + name);

for (const pack of Object.keys(iconMaps))
  for (const name of [
    'constructor',
    '__proto__',
    'toString',
    'material-design:constructor'
  ])
    assert.equal(resolveIcon(name, pack), undefined, 'Unknown icon: ' + name);

for (const pack of ['material-design', 'fontawesome-solid', 'fluent-system']) {
  for (const [legacy, semantic] of Object.entries({
    WORK: 'workspaces',
    work: 'workspaces',
    EDIT: 'edit',
    DELETE: 'delete',
    ADD: 'add',
    CALENDAR: 'calendar',
    GROUP_LINK: 'group',
    LOCK: 'lock',
    JUMP: 'open-in-new'
  })) {
    assert(resolveIcon(legacy, pack), legacy + ' must resolve in ' + pack);
    assert.deepEqual(resolveIcon(legacy, pack), resolveIcon(semantic, pack));
  }
}
