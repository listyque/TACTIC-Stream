import assert from 'node:assert/strict';
import * as Chart from '../../src/tactic_stream/shared_ui/controls/charts/chart.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

for (const width of [120, 320, 520, 1000])
  for (const type of ['bar', 'line', 'donut']) {
    const data = {
      type,
      labels: ['First', 'Second', 'Missing', 'Fourth'],
      values: [12, 4, null, 8]
    };
    const scene = Chart.describe(data, 'chart', width, 240, 'ru');
    validateScene(scene);
    const g = scene.nodes[0].chart;
    assert.equal(g.values[2], null);
    if (type === 'donut') {
      assert.equal(g.total, 24);
      assert.equal(Chart.hit(g, g.cx, g.cy), -1);
      assert.equal(Chart.hit(g, g.cx, g.cy - (g.inner + g.radius) / 2), 0);
    } else {
      assert.equal(Chart.hit(g, g.marks[1].x, g.plot.y + 5), 1);
      assert.equal(Chart.hit(g, 0, 0), -1);
    }
    const paths = [];
    const context = new Proxy(
      {},
      {
        get:
          (_, name) =>
          (...args) => {
            for (const value of args)
              if (typeof value === 'number') assert(Number.isFinite(value));
            paths.push(name);
          }
      }
    );
    Chart.paint(context, g, () => '#55aabb', 1);
    assert(
      paths.includes(
        type === 'donut' ? 'arc' : type === 'bar' ? 'fillRect' : 'lineTo'
      )
    );
  }
const signed = Chart.geometry({ type: 'bar', values: [-10, 0, 20] }, 500, 240);
assert.equal(Chart.number(1234.5, 'ru'), '1 234,5');
assert.equal(Chart.axisLabel('2026-10-10', 'en'), '10 Oct');
assert.equal(Chart.axisLabel('2026-10-10', 'ru'), '10 окт');
assert(signed.marks[0].y > signed.marks[0].zero);
assert(signed.marks[2].y < signed.marks[2].zero);
assert.equal(
  Chart.geometry({ type: 'donut', values: [-1, 2] }, 500, 240).valid,
  false
);
assert.equal(
  Chart.geometry({ type: 'donut', values: [0, null] }, 500, 240).total,
  0
);
console.log(
  'Charts: shared bounds, painting, hover, signed values, null gaps and empty rings pass.'
);
