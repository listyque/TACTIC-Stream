// Run against an initialized, isolated desktop data root, never a user's profile.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';
import { _electron } from 'playwright';

const [bundle, dataRoot] = process.argv.slice(2).map(item => path.resolve(item));
assert(process.env.WINDOWS_CHECK_PASSWORD, 'Set WINDOWS_CHECK_PASSWORD for the owned test database');
const run = promisify(execFile);
const monitor = path.join(dataRoot, 'server/temp/log/monitor.json');
const environment = { ...process.env, PATH: process.env.SystemRoot + '/System32', PYTHONPATH: 'invalid-python-path', PYTHONHOME: 'invalid-python-home' };
delete environment.ELECTRON_RUN_AS_NODE;
const errors = [];
let address;

async function stopped(app, status) {
  const exit = new Promise(resolve => app.process().once('exit', resolve));
  await app.evaluate(({ app }) => app.quit());
  await Promise.race([exit, new Promise((_, reject) => setTimeout(() => reject(new Error('Desktop failed to exit')), 40000).unref())]);
  assert.equal(JSON.parse(await fs.readFile(monitor, 'utf8')).state, 'stopped');
  for (const pid of [status.monitor_pid, ...status.workers.map(item => item.pid)]) {
    assert.throws(() => process.kill(pid, 0), /ESRCH/, 'Owned server process survived: ' + pid);
  }
}

for (let iteration = 0; iteration < 2; iteration++) {
  const args = iteration === 0 ? ['--data-dir', dataRoot] : ['--data-dir=' + dataRoot];
  const app = await _electron.launch({ executablePath: path.join(bundle, 'TACTIC Stream.exe'), args, env: environment, timeout: 120000 });
  const child = app.process();
  child.stderr.on('data', chunk => process.stderr.write(chunk));
  let status;
  try {
    assert.equal(await app.evaluate(({ app }) => app.getPath('userData')), path.join(dataRoot, 'browser'));
    const page = await app.firstWindow({ timeout: 120000 });
    page.on('pageerror', error => errors.push(error.message));
    page.setDefaultTimeout(30000);
    await page.waitForURL('http://127.0.0.1:*/**');
    assert.equal(await page.evaluate(() => typeof window.require), 'undefined');
    status = JSON.parse(await fs.readFile(monitor, 'utf8'));
    assert.equal(status.state, 'running');
    if (iteration === 0) {
      address = new URL(page.url()).origin;
      await page.getByLabel('Login', { exact: true }).fill('admin');
      await page.getByLabel('Password', { exact: true }).fill(process.env.WINDOWS_CHECK_PASSWORD);
      await page.getByRole('button', { name: 'Sign in', exact: true }).click();
      await page.locator('.project-picker').waitFor();
      await page.evaluate(() => localStorage.setItem('portable-check', 'preserved'));
      const check = path.resolve('../tools/handler_deployment_check.py');
      const result = await run(path.join(bundle, 'runtime/python.exe'), ['-I', '-B', '-X', 'utf8', '-c',
        "import json,os,runpy,secrets,sys; from pathlib import Path; ns=runpy.run_path(sys.argv[1]); print(json.dumps(ns['check'](sys.argv[2],Path(sys.argv[3]),os.environ['WINDOWS_CHECK_PASSWORD'],secrets.token_hex(6),Path(sys.argv[4]))))",
        check, address, path.join(bundle, 'TACTIC-Handler'), dataRoot], { env: environment, timeout: 120000 });
      console.log('Handler SDK:', result.stdout.trim());
      await page.screenshot({ path: path.join(dataRoot, 'desktop.png') });
    } else {
      assert.equal(new URL(page.url()).origin, address);
      assert.equal(await page.evaluate(() => localStorage.getItem('portable-check')), 'preserved');
      await page.locator('.project-picker').waitFor();
    }
    await stopped(app, status);
  } catch (error) {
    console.error(error);
    if (child.exitCode === null) await app.close();
    throw error;
  }
}
assert.deepEqual(errors, []);
console.log(JSON.stringify({ desktop: 'passed', restart: 'passed', owned_workers_stopped: true, address }));
