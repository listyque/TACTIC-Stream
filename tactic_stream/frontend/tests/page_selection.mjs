import assert from "node:assert/strict";
import * as Selection from "../../src/tactic_stream/shared_ui/features/administration/layouts/page.selection.mjs";
import * as State from "../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs";
import * as Document from "../../src/tactic_stream/shared_ui/features/administration/layouts/page.document.mjs";
import * as Layout from "../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs";
const boxes = [
  { key: "0", x: 0, y: 0, width: 500, height: 500 },
  { key: "0.0", x: 20, y: 20, width: 80, height: 40 },
  { key: "0.1", x: 160, y: 80, width: 100, height: 60 },
  { key: "1", x: 350, y: 20, width: 40, height: 30 },
];
assert.deepEqual(Selection.toggle(["0"], "0.0"), ["0.0"]);
assert.deepEqual(Selection.roots(["0", "0.0", "1"]), ["0", "1"]);
assert.deepEqual(
  Selection.marquee(boxes, { x: 10, y: 10 }, { x: 270, y: 150 }),
  ["0.0", "0.1"],
);
const selected = Selection.selected(boxes, ["0.0", "0.1"]);
const aligned = Selection.alignment(selected, "left");
assert.equal(aligned[1].after.x, 20);
assert.equal(aligned[1].after.width, 100);
const dragged = Selection.drag(selected, "move", 4, 2, boxes, 0.5, true);
assert.ok(dragged.guides.some((guide) => guide.axis === "y"));
assert.equal(dragged.changes[1].after.x - dragged.changes[0].after.x, 140);
assert.equal(
  Selection.drag(selected, "move", 4, 2, boxes, 0.5, false).guides.length,
  0,
);
const doc = {
  name: "selection",
  title: "Selection",
  blocks: [
    {
      kind: "column",
      children: [
        { kind: "text", text: "A" },
        { kind: "text", text: "B" },
      ],
    },
  ],
};
const before = Document.fingerprint(doc);
let model = { document: doc, canWrite: true };
let ui = State.initial();
function dispatch(event) {
  const result = State.transition(ui, model, event);
  assert.equal(result.ui.error, "");
  ui = result.ui;
  for (const command of result.commands)
    if (command.type === "document")
      model = { ...model, document: command.document };
  return result;
}
dispatch({ type: "selection", keys: ["0.0", "0.1"] });
assert.equal(ui.past.length, 0);
dispatch({ type: "align", value: "left", boxes });
assert.equal(model.document.blocks[0].children[1].offset_x, -140);
assert.equal(ui.past.length, 1);
dispatch({ type: "undo" });
assert.equal(Document.fingerprint(model.document), before);
assert.deepEqual(ui.selection, ["0.0", "0.1"]);
dispatch({ type: "redo" });
assert.equal(model.document.blocks[0].children[1].offset_x, -140);
dispatch({ type: "appearance", field: "shadow", value: true });
assert.ok(
  model.document.blocks[0].children.every((item) => item.appearance.shadow),
);
dispatch({ type: "buffer", key: "style", value: "3" });
dispatch({ type: "appearanceCommit", key: "style", field: "stroke_width" });
assert.ok(
  model.document.blocks[0].children.every(
    (item) => item.appearance.stroke_width === 3,
  ),
);
const edited = Document.fingerprint(model.document);
const invalid = State.transition(ui, model, {
  type: "geometry",
  value: {
    changes: [
      {
        key: "0.0",
        handle: "move",
        position: true,
        before: { x: 0, y: 0 },
        after: { x: 10, y: 10 },
      },
      {
        key: "0.1",
        handle: "move",
        position: true,
        before: { x: 0, y: 0 },
        after: { x: 99999, y: 0 },
      },
    ],
  },
});
assert.ok(invalid.ui.error);
assert.equal(invalid.commands.length, 0);
assert.equal(Document.fingerprint(model.document), edited);
assert.equal(
  State.transition(
    ui,
    { ...model, canWrite: false },
    { type: "align", value: "left", boxes },
  ).commands.length,
  0,
);
assert.equal(
  State.transition({ ...ui, preview: true }, model, {
    type: "appearance",
    field: "shadow",
    value: false,
  }).commands.length,
  0,
);
assert.throws(() =>
  Document.appearances(doc, ["0.0"], "stroke", "url(https://example.com)"),
);
const scene = Layout.describe(
  {
    layoutDesigning: false,
    layoutNodes: [
      {
        kind: "text",
        text: "Styled",
        height: 60,
        width: "160px",
        editorPath: [0],
        offsetX: 12,
        offsetY: 8,
        appearance: {
          fill: "panel",
          stroke: "#FF0000",
          stroke_width: 2,
          radius: 6,
          shadow: true,
          animate: true,
        },
      },
    ],
  },
  500,
  400,
  "en",
  true,
  "",
);
const content = scene.nodes.find(
  (node) => node.id === "customLayoutScroll",
).children;
const styled = content.find((node) => node.id === "customLayout_0_block");
assert.equal(styled.x, 12);
assert.equal(styled.y, 8);
assert.equal(styled.borderWidth, 2);
assert.equal(styled.radius, 6);
assert.ok(styled.motion.y);
assert.equal(content.filter((node) => node.id.includes("_shadow")).length, 2);
assert.equal(Document.fingerprint(doc), before);
const metrics = Layout.describe(
  {
    layoutNodes: [
      { kind: "metric", value: 2, height: 80, editorPath: [0] },
      {
        kind: "metric",
        value: 2,
        height: 80,
        editorPath: [1],
        appearance: {
          fill: "panel",
          stroke: "outlineVariant",
          stroke_width: 1,
          radius: 6,
          shadow: true,
        },
      },
    ],
  },
  500,
  400,
  "en",
  true,
  "",
);
const metricNodes = metrics.nodes.find(
  (node) => node.id === "customLayoutScroll",
).children;
assert.equal(
  metricNodes.find((node) => node.id === "customLayout_0_block").children[0]
    .border,
  "outlineVariant",
);
const metric = metricNodes.find((node) => node.id === "customLayout_1_block");
assert.equal(metric.children[0].border, "");
assert.equal(metric.children[0].height, 80);
assert.equal(metric.borderWidth, 1, "A decorated metric has one surface");
console.log(
  "Page selection: group geometry/history, marquee, snapping, alignment, style and atomic guards pass",
);
