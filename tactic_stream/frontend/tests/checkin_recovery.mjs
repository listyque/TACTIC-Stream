import assert from 'node:assert/strict';
import Recovery, { queueId } from '../src/features/checkin/queue/recovery.js';
import { stagePublication } from '../src/features/checkin/queue/publication.js';

globalThis.localStorage = Object.create(null, {
  setItem: {
    value(key, value) {
      this[key] = value;
    }
  },
  getItem: {
    value(key) {
      return this[key] ?? null;
    }
  },
  removeItem: {
    value(key) {
      delete this[key];
    }
  }
});
const owner = () => ({
  ...Recovery,
  login: 'artist',
  ticket: 'temporary',
  jobs: [],
  persisted: new Map(),
  sequence: 0,
  $emit() {}
});
const first = owner(),
  second = owner();
const draft = (name) => ({
  recoveryId: queueId(),
  project: 'one',
  searchKey: 'cg/shot?code=SH1',
  name
});
first.restore();
second.restore();
first.jobs.push(draft('First tab'));
first.changed();
second.jobs.push(draft('Second tab'));
second.changed();
const restored = owner();
restored.restore();
assert.deepEqual(restored.jobs.map((job) => job.name).sort(), [
  'First tab',
  'Second tab'
]);
assert.ok(restored.jobs.every((job) => job.status === 'Missing files'));
assert.ok(
  Object.values(localStorage).every((value) => !value.includes('temporary'))
);
first.forgetJob(first.jobs[0]);
const remaining = owner();
remaining.restore();
assert.deepEqual(
  remaining.jobs.map((job) => job.name),
  ['Second tab']
);

const job = second.jobs[0];
job.files = [new File(['source'], 'source.txt')];
job.previews = [];
job.submission = {
  batch: job.recoveryId + '-0',
  options: { source_files: [{ path: 'source.txt', size: 6 }] }
};
job.status = 'Uploading';
second.changed();
const afterRefresh = owner();
afterRefresh.restore();
assert.equal(afterRefresh.jobs[0].status, 'Checking in');
assert.deepEqual(afterRefresh.jobs[0].submission, job.submission);

const requests = [];
globalThis.fetch = async (_url, { body }) => {
  requests.push([
    body.get('batch_id'),
    body.get('chunk_id'),
    body.get('operations'),
    await body.get('file').text()
  ]);
  if (requests.length === 1) throw new Error('Connection lost');
  return Response.json({ result: { accepted: true, duplicate: true } });
};
await assert.rejects(
  stagePublication(job, undefined, () => {}),
  /Connection lost/
);
await stagePublication(
  { ...afterRefresh.jobs[0], files: job.files },
  undefined,
  () => {}
);
assert.deepEqual(requests[0], requests[1]);
