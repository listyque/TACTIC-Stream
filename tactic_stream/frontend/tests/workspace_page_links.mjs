import assert from 'node:assert/strict';
import {
  customPageLink,
  customUrlLocation
} from '../src/features/workspace/links.js';

const origin = 'http://tactic.test:8081';
for (const name of ['work', 'tasks', 'analytics']) {
  const path = '/projects/demo/dashboard/' + name;
  for (const href of [path, origin + path]) {
    const address = customPageLink(href, origin);
    assert.equal(address.pathname, path);
    assert.equal(customUrlLocation(address).path, '/dashboard/' + name);
  }
}
assert.equal(
  customPageLink('/projects/demo/#/review/CAR?q=1', origin).hash,
  '#/review/CAR?q=1'
);
for (const href of [
  'https://other.test/projects/demo/dashboard/work',
  'https://tactic.test:8081/projects/demo/dashboard/work',
  'http://user:password@tactic.test:8081/projects/demo/dashboard/work',
  'javascript:alert(1)',
  origin + '/projects/demo/dashboard/wo\nrk',
  '/projects/demo/dashboard/\\work',
  'https://[bad',
  '/admin/',
  '/projects/demo/'
])
  assert.equal(customPageLink(href, origin), null, href);
console.log(
  'PASS: dashboard page links stay in the connected origin; foreign URLs retain external routing'
);
