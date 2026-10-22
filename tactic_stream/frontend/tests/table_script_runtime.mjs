import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { route } from '../../src/tactic_stream/shared_ui/features/table/actions.state.mjs';
import vm from 'node:vm';

const client = await readFile(
  new URL('../../src/pyasm/common/js/client_api.js', import.meta.url),
  'utf8'
);
const runtime = await readFile(
  new URL(
    '../../src/tactic_stream/compatibility/table_action_runtime.js',
    import.meta.url
  ),
  'utf8'
);
for (const [name, expected] of [
  ['client_api.js', client],
  ['table_action_runtime.js', runtime]
]) {
  assert.equal(
    await readFile(
      'D:/grav/Tactic Stream/TH/thlib/ui/qml/features/table/runtime/' + name,
      'utf8'
    ),
    expected,
    'Both products ship an independent exact copy of ' + name
  );
}
function run(code, confirmation) {
  const calls = [];
  const context = vm.createContext({
    call: (...args) => {
      calls.push(args);
      return args[0] === 'query' ? [{ code: 'A' }] : { status: 'OK' };
    }
  });
  vm.runInContext(client + '\n' + runtime, context);
  context.input = {
    project: 'one',
    searchType: 'contract/entity',
    column: 'action',
    view: 'table',
    record: { language: 'python' },
    searchKey: 'contract/entity?project=one&code=A',
    searchKeys: [
      'contract/entity?project=one&code=A',
      'contract/entity?project=one&code=B'
    ],
    confirmation
  };
  const result = vm.runInContext(
    'runTableAction(function(bvr,evt,spt,TacticServerStub,alert,console,window,confirm){\n' +
      code +
      '\n},input,call)',
    context
  );
  return {
    result: JSON.parse(JSON.stringify(result)),
    calls: JSON.parse(JSON.stringify(calls))
  };
}
const query = run(
  `var server=TacticServerStub.get(); var rows=server.query('contract/entity',{filters:[['code','A']],limit:2}); return rows;`
);
assert.deepEqual(query.result.output, [{ code: 'A' }]);
assert.deepEqual(query.calls, [
  ['query', ['contract/entity'], { filters: [['code', 'A']], limit: 2 }, 'one']
]);
const code = `if(confirm('Uninstall this plugin?')) {var server=TacticServerStub.get();server.execute_cmd('tactic.command.PluginUninstaller',{manifest:'fixture'});}`;
assert.deepEqual(run(code).result, {
  confirmation: 'Uninstall this plugin?',
  commands: [],
  calls: 0
});
assert.equal(run(code).calls.length, 0);
assert.equal(
  run(code, { message: 'Uninstall this plugin?', accepted: false }).calls
    .length,
  0
);
const accepted = run(code, {
  message: 'Uninstall this plugin?',
  accepted: true
});
assert.deepEqual(accepted.calls, [
  [
    'execute_cmd',
    ['tactic.command.PluginUninstaller', { manifest: 'fixture' }, {}],
    {},
    'one'
  ]
]);
const caught = run(
  `try{confirm('Continue?')}catch(error){} try{TacticServerStub.get().update(bvr.search_key,{name:'bad'})}catch(error){}`
);
assert.equal(caught.calls.length, 0);
assert.equal(caught.result.confirmation, 'Continue?');
const rows = run(
  `return spt.table.get_selected_rows().map(function(row){return row.getAttribute('spt_search_key')});`
);
assert.deepEqual(rows.result.output, [
  'contract/entity?project=one&code=A',
  'contract/entity?project=one&code=B'
]);
const popup = run(
  `var tab_top=bvr.src_el.getParent('.spt_tab_top');var popup=spt.panel.load_popup('Edit','tactic.ui.panel.EditWdg',{search_key:bvr.search_key});popup.on_save_cbk=function(){spt.tab.set_tab_top(tab_top);spt.tab.reload_selected();}`
);
assert.equal(popup.result.commands[0].refreshOnSave, true);
assert.throws(
  () => run(`bvr.src_el.getParent('.invented_dom_widget')`),
  /Unsupported table selector/
);
assert.throws(() => run(`return Promise.resolve('lost')`), /Promise results/);
assert.throws(
  () =>
    run(
      `TacticServerStub.get().update(bvr.search_key,{name:'saved'});confirm('Too late?')`
    ),
  /Confirm before making server calls/
);
console.log(
  'PASS: original table script API, row/selection scope, safe confirmation and explicit unsupported paths'
);

const custom = run('alert(bvr.kwargs.search_key);');
assert.equal(
  custom.result.commands[0].text,
  'contract/entity?project=one&code=A'
);

// Execute the unchanged CG JavaScript against the fake SDK; no project command runs.
const cg = await readFile(
  new URL('../../../cg/config_custom_script.spt', import.meta.url),
  'utf8'
);
const projectScripts = cg
  .split('#-- Start Entry --#')
  .filter((block) =>
    block.includes('insert.set_value(\'language\', """javascript""")')
  );
assert.equal(projectScripts.length, 3);
for (const block of projectScripts) {
  const code = block.match(
    /insert\.set_value\('script', """([\s\S]*?)"""\)/
  )[1];
  const action = run(code);
  assert.equal(action.calls.length, 1);
  assert.equal(action.calls[0][0], 'execute_python_script');
  assert.equal(
    action.calls[0][1][1].search_key,
    'contract/entity?project=one&code=A'
  );
}

assert.deepEqual(
  run('return TacticServerStub.get().split_search_key(bvr.search_key);').result
    .output,
  ['contract/entity?project=one', 'A']
);

const configurations = new URL(
  '../../src/tactic_stream/config/search_type/widget/',
  import.meta.url
);
let configuredButtons = 0;
for (const name of await readdir(configurations, { recursive: true })) {
  if (!name.endsWith('.xml')) continue;
  const xml = await readFile(
    new URL(name.replaceAll('\\', '/'), configurations),
    'utf8'
  );
  for (const match of xml.matchAll(
    /<display\b[^>]*class=["'][^"']*ButtonElementWdg["'][^>]*>([\s\S]*?)<\/display>/g
  )) {
    const body = match[1].match(/<cbjs_action>([\s\S]*?)<\/cbjs_action>/)?.[1];
    if (!body) continue;
    const code = body.includes('<![CDATA[')
      ? body.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
      : body
          .replaceAll('&lt;', '<')
          .replaceAll('&gt;', '>')
          .replaceAll('&quot;', '"')
          .replaceAll('&apos;', "'")
          .replaceAll('&amp;', '&');
    let action = run(code);
    if (action.result.confirmation)
      action = run(code, {
        message: action.result.confirmation,
        accepted: true
      });
    action.result.commands.forEach(route);
    configuredButtons++;
  }
}
assert.equal(configuredButtons, 16);
console.log(
  'PASS:',
  configuredButtons,
  'shipped XML button actions retain their existing owners'
);
