import assert from 'node:assert/strict';
import { viewActions } from '../../src/tactic_stream/shared_ui/features/table/menus.ui.mjs';

const views = [{ view: 'table', title: 'Default table', current: true }];
for (const language of ['en', 'ru']) {
  for (const stream of [false, true]) {
    const actions = viewActions(views, true, language, false, stream);
    const commands = actions.map((action) => action.command).filter(Boolean);
    assert.equal(commands.includes('manage'), stream);
    for (const command of [
      'select:0',
      'configure',
      'save_as',
      'scroll_columns'
    ]) {
      assert.ok(commands.includes(command), command);
    }
  }
}
console.log(
  'Legacy table menus preserve native actions and hide the Stream manager'
);
