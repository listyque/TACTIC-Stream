import assert from 'node:assert/strict';
import { observeFrameSizes } from '../src/frame/resize.js';

const scheduled = new Map();
let delivery;
let serial = 0;
globalThis.ResizeObserver = class {
  constructor(callback) {
    delivery = callback;
  }
  observe() {}
  unobserve() {}
  disconnect() {}
};
globalThis.requestAnimationFrame = (callback) => {
  scheduled.set(++serial, callback);
  return serial;
};
globalThis.cancelAnimationFrame = (id) => scheduled.delete(id);
const body = {},
  toolbar = {},
  calls = [];
const observer = observeFrameSizes((entries) => calls.push(entries));
const entry = (target, width) => ({
  target,
  contentRect: { width, height: 100 }
});
const flush = () => {
  const callbacks = [...scheduled.values()];
  scheduled.clear();
  callbacks.forEach((callback) => callback());
};
delivery([entry(body, 640)]);
delivery([entry(toolbar, 900)]);
delivery([entry(body, 720)]);
assert.equal(scheduled.size, 1);
flush();
assert.deepEqual(calls[0], [entry(body, 720), entry(toolbar, 900)]);
delivery([entry(body, 800), entry(toolbar, 1000)]);
observer.unobserve(body);
flush();
assert.deepEqual(calls[1], [entry(toolbar, 1000)]);
delivery([entry(body, 999)]);
observer.disconnect();
flush();
delivery([entry(toolbar, 999)]);
assert.equal(scheduled.size, 0);
assert.equal(calls.length, 2);
let delivered = 0;
const reentrant = observeFrameSizes(() => {
  delivered++;
  if (delivered === 1) delivery([entry(toolbar, 700)]);
});
delivery([entry(body, 600)]);
flush();
assert.equal(delivered, 1);
assert.equal(scheduled.size, 1);
flush();
assert.equal(delivered, 2);
reentrant.disconnect();
console.log(
  'Frame resize: multi-target deliveries, latest values, unobserve and disposal passed.'
);
