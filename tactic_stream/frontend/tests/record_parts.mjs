import assert from "node:assert/strict";
import * as Parts from "../../src/tactic_stream/shared_ui/features/table/record.parts.mjs";
import * as State from "../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs";
import * as Layout from "../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs";

const item = {
  kind: "form",
  editorPath: [1],
  form: {
    searchKey: "demo/asset?code=A",
    expectedRevision: "R1",
    configRevision: "C1",
    scope: { view: "dashboard.test", path: [1] },
    fields: [
      { name: "count", title: "Count", type: "text", value: 0 },
      { name: "ready", title: "Ready", type: "bool", value: false },
      { name: "code", title: "Code", type: "text", value: "A", readOnly: true },
    ],
  },
};
const document = { layoutNodes: [item] },
  key = Parts.key(item);
let store = Parts.change({}, document, {
  key,
  intent: "value",
  name: "count",
  value: "12",
}).store;
store = Parts.change(store, document, {
  key,
  intent: "value",
  name: "ready",
  value: true,
}).store;
assert.equal(Parts.entry(store, item).values.ready, true);
assert.equal(Parts.entry(store, item).values.code, "A");
assert.equal(
  Parts.change(store, document, {
    key,
    intent: "value",
    name: "code",
    value: "B",
  }).store,
  store,
);
let result = Parts.change(store, document, { key, intent: "save" });
assert.deepEqual(result.command.values, { count: "12", ready: true });
assert.equal(result.command.expected_revision, "R1");
assert.equal(
  Parts.change(result.store, document, { key, intent: "save" }).command,
  undefined,
);
store = Parts.settled(result.store, key, null, {
  message: "Disconnected",
  uncertain: true,
});
assert.equal(
  Parts.change(store, document, { key, intent: "save" }).command,
  undefined,
);
assert.ok(Parts.change(store, document, { key, intent: "check" }).command);
store = Parts.settled(store, key, { state: "conflict" });
assert.equal(
  Parts.change(store, document, { key, intent: "save" }).command,
  undefined,
);
assert.deepEqual(
  Parts.change(store, document, { key, intent: "cancel" }).store,
  {},
);
assert.deepEqual(Parts.settled(result.store, key, { state: "saved" }), {});
assert.equal(Parts.interrupted(result.store)[key].uncertain, true);
assert.equal(Parts.interrupted(result.store)[key].busy, false);
const other = {
  ...item,
  form: { ...item.form, searchKey: "demo/asset?code=B" },
};
assert.notEqual(Parts.key(other), key);
assert.equal(
  Parts.entry(result.store, other).values.count,
  0,
  "Another selected record never inherits this draft",
);
const model = {
  canWrite: true,
  document: {
    name: "new",
    title: "New",
    blocks: [{ kind: "form", fields: ["name"] }],
  },
};
const ui = { ...State.initial(), selected: "0", selection: ["0"] };
assert.deepEqual(
  State.transition(ui, model, {
    type: "formField",
    name: "status",
    value: true,
  }).commands[0].document.blocks[0].fields,
  ["name", "status"],
);
assert.equal(
  State.transition(
    ui,
    { ...model, canWrite: false },
    { type: "formField", name: "status", value: true },
  ).commands.length,
  0,
);
const part = Parts.field(
  { text: "Progress", value: 0, format: "progress" },
  "progress",
  200,
);
assert.equal(
  part.children.find((node) => node.id === "progress_progress").width,
  0,
);
assert.equal(
  Parts.field({ value: null, format: "badge" }, "status", 200).children[0].text,
  "—",
);
const scene = Layout.describe({ layoutNodes: [item] }, 800, 700, "en");
assert.ok(scene.nodes.length);
const form = Parts.describe(item, "form", 700, {}, "en", false);
assert.ok(
  form.children.filter((node) => node.action).every((node) => !node.enabled),
  "Editor preview never edits data",
);
console.log(
  "Record parts: bound zero/false/NULL, native form controls, draft isolation, revision capture, explicit save/recovery/cancel and editor guards pass",
);
