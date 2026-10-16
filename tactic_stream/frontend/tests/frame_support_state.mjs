import assert from 'node:assert/strict';
import * as Editor from '../../src/tactic_stream/shared_ui/features/support/identity/profile.editor.state.mjs';
import * as SignIn from '../../src/tactic_stream/shared_ui/features/support/connection/sign_in.ui.mjs';
import * as Updates from '../../src/tactic_stream/shared_ui/features/support/connection/updates.ui.mjs';
import { matchesUser } from '../../src/tactic_stream/shared_ui/features/support/identity/profile.ui.mjs';
import { selection } from '../../src/tactic_stream/shared_ui/features/support/diagnostics/performance.ui.mjs';

const snapshot = {
  login: 'artist',
  address: 'Studio 4',
  groups: ['artists'],
  accessLevels: { artists: 'low' }
};
const original = Editor.begin(snapshot);
assert.equal(original.password, '');
let draft = Editor.edit(original, {
  type: 'field',
  key: 'address',
  value: 'Studio 8'
});
draft = Editor.edit(draft, { type: 'group', code: 'reviewers', value: true });
draft = Editor.edit(draft, { type: 'group', code: 'reviewers', value: true });
draft = Editor.edit(draft, { type: 'access', code: 'artists', value: 'high' });
assert.deepEqual(original, { ...snapshot, password: '' });
assert.deepEqual(draft.groups, ['artists', 'reviewers']);
assert.equal(original.accessLevels.artists, 'low');
assert(Editor.dirty(draft, original, false));
assert.throws(
  () => Editor.edit(draft, { type: 'field', key: 'unexpected', value: 'no' }),
  /Unknown profile field/
);
assert.equal(Editor.closeDecision({ saving: true, dirty: true }, true), 'busy');
assert.equal(
  Editor.closeDecision({ dirty: false, uncertain: true }, false),
  'confirm'
);
assert.equal(Editor.closeDecision({ dirty: true }, true), 'close');
assert.equal(
  Editor.page({ mode: 'profile', canManage: true, restricted: true }, 'groups'),
  'profile'
);
assert.equal(
  Editor.page({ mode: 'profile', canManage: true }, 'groups'),
  'groups'
);
assert.equal(
  Editor.submitted({ ...draft, password: 'fixture-secret' }).password,
  ''
);
assert(!SignIn.canSubmit({ login: 'artist', password: '' }));
assert(!SignIn.canSubmit({ login: 'artist', password: 'fixture', busy: true }));
assert(
  !SignIn.canSubmit({ login: 'artist', password: 'fixture', ready: false })
);
assert(SignIn.canSubmit({ login: 'artist', password: 'fixture' }));
assert.deepEqual(
  Updates.versionValues({
    major: '0',
    minor: '6',
    build: '0',
    revision: '108'
  }),
  [0, 6, 0, 108]
);
for (const revision of ['-1', '1.5', '1000', 'NaN', ''])
  assert.equal(
    Updates.versionValues({ major: '0', minor: '6', build: '0', revision }),
    null
  );
assert.equal(
  Updates.stepVersion({ revision: '999' }, 'revision', 1).revision,
  '999'
);
assert.equal(
  Updates.stepVersion({ revision: '0' }, 'revision', -1).revision,
  '0'
);
assert(
  matchesUser(
    {
      login: 'artist',
      displayName: 'Alice',
      email: 'mail@example.test',
      groups: ['Studio Artists']
    },
    ' studio '
  )
);
assert(
  matchesUser(
    { login: 'artist', groups: [{ code: 'team', label: 'Studio' }] },
    'studio'
  )
);
assert.equal(selection([], 0, 'ArrowDown'), null);
assert.equal(
  selection([{ sampleId: 1 }, { sampleId: 2 }], 2, 'ArrowDown').sampleId,
  2
);
console.log(
  'Support: immutable drafts, membership/access, close/unknown-write rules, secret clearing, credentials, versions, identity search and selection passed.'
);
