import assert from 'node:assert/strict';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as MCP from '../../src/tactic_stream/shared_ui/features/configuration/mcp.ui.mjs';

const tools = [
  {
    name: 'agent_context',
    title: 'Project context',
    description: 'Read the current project and selection.',
    readonly: true
  },
  {
    name: 'ts_dashboard_save',
    title: 'Save dashboard',
    description: 'Save the revisioned page configuration.',
    readonly: false
  }
];
let model = { ...MCP.initial(), project: 'demo', enabled: true, tools };
const flatten = (nodes) =>
  nodes.flatMap((node) => [node, ...flatten(node.children || [])]);
for (const width of [320, 600, 800])
  for (const height of [420, 650])
    for (const language of ['en', 'ru']) {
      const scene = MCP.describe(model, width, height, language);
      validateScene(scene);
      const all = flatten(scene.nodes),
        get = (id) => all.find((node) => node.id === id);
      assert.ok(get('mcpToolSurface').border);
      for (const [index, tool] of tools.entries()) {
        const row = get('mcpTool_' + index);
        assert.equal(row.text, tool.title);
      assert.ok(row.label.includes(tool.title));
      assert.ok(row.label.includes(get('mcpToolAccess_' + index).text));
        assert.equal(get('mcpToolName_' + index).text, tool.title);
        assert.equal(get('mcpToolDescription_' + index).text, tool.description);
        assert.ok(get('mcpToolAccess_' + index).text);
        for (const child of row.children) {
          assert.ok(child.x >= 0 && child.x + child.width <= row.width);
          assert.ok(child.y >= 0 && child.y + child.height <= row.height);
        }
      }
      assert.ok(
        get('mcpTitle').x + get('mcpTitle').width <= get('mcpLifetime').x ||
          get('mcpTitle').y + get('mcpTitle').height <= get('mcpLifetime').y
      );
      assert.ok(
        get('mcpCreate').y > get('mcpScroll').y + get('mcpScroll').height
      );
      assert.equal(get('mcpCreate').enabled, false);
    }
model = MCP.edit(model, { type: 'field', field: 'title', value: 'Review' });
model = MCP.edit(model, { type: 'readonly' });
assert.deepEqual(model.selected, ['agent_context']);
assert.equal(
  flatten(MCP.describe(model, 800, 650, 'en').nodes).find(
    (n) => n.id === 'mcpCreate'
  ).enabled,
  true
);
model = MCP.edit(model, { type: 'clear' });
assert.deepEqual(model.selected, []);
const busy = flatten(
  MCP.describe({ ...model, busy: true }, 800, 650, 'en').nodes
);
assert.ok(
  busy
    .filter((n) =>
      ['mcpReadTools', 'mcpClearTools', 'mcpTool_0', 'mcpCreate'].includes(n.id)
    )
    .every((n) => !n.enabled)
);
console.log(
  'PASS: named MCP permission rows, explanations, access type, responsive geometry and explicit permission selection'
);
