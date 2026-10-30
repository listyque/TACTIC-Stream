<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { copyText } from '../../controls/clipboard.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/diagnostics/system.ui.mjs';

const props = defineProps({ ticket: String, project: String });
const dialog = ref(null),
  host = ref(null),
  size = ref({ width: 800, height: 600 });
const model = ref(UI.initial());
const emit = defineEmits(['navigation-cleared']);
const scene = computed(() =>
  UI.describe(
    model.value,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
let generation = 0,
  observer;
watch(host, (element) => {
  observer?.disconnect();
  if (element) {
    observer = observeFrameSizes((entries) => {
      const box = entries.at(-1).contentRect;
      size.value = { width: box.width, height: box.height };
    });
    observer.observe(element);
  }
});
function clear() {
  ++generation;
  model.value = UI.initial();
}
watch(
  () => [props.ticket, props.project],
  () => {
    clear();
    dialog.value?.close();
  }
);
onBeforeUnmount(() => {
  clear();
  observer?.disconnect();
});
function refresh() {
  return run('info');
}
async function run(kind, plan = UI.testPlan(model.value)) {
  if (!props.ticket || model.value.busy) return;
  const id = ++generation;
  model.value.busy = true;
  model.value.pending = kind;
  model.value.error = '';
  const owner = { ticket: props.ticket, project: props.project || 'admin' };
  let stopped = false;
  async function call(method, values = {}) {
    if (stopped || id !== generation) throw Error('Test cancelled');
    return rpc(
      'execute_class_method',
      [owner, 'tactic.ui.app.system_info_wdg.SystemInfoWdg', method, values],
      {},
      true
    );
  }
  try {
    let result;
    if (kind === 'info') result = await call('get_info');
    else if (kind === 'balance') {
      const samples = [];
      do {
        samples.push(await call('connection_probe'));
      } while (!UI.balanceComplete(samples));
      result = { samples };
    } else if (kind === 'performance') {
      const count = plan.iterations,
        parallel = Math.min(8, count);
      let started = performance.now();
      for (let index = 0; index < count; index++)
        await call('performance_probe');
      const sequentialMs = performance.now() - started;
      let next = 0;
      started = performance.now();
      await Promise.all(
        Array.from({ length: parallel }, async () => {
          while (next++ < count) await call('performance_probe');
        })
      );
      result = {
        sequentialMs,
        parallelMs: performance.now() - started,
        count,
        parallel
      };
    } else if (kind === 'handoff') {
      throw Error(
        'The browser cannot inspect client folders. Run this test in TACTIC Handler.'
      );
    } else {
      const values =
        kind === 'email'
          ? { sender: model.value.sender, recipients: model.value.recipients }
          : kind === 'script'
            ? { path: model.value.scriptPath }
            : {};
      result = await call('run_test', { action: kind, values });
    }
    if (id !== generation) return;
    if (kind === 'info') {
      Object.assign(model.value, result);
      if (!model.value.loaded)
        model.value.sender = model.value.recipients = result.mailFrom || '';
      model.value.loaded = true;
      model.value.sections = [
        ...result.sections,
        {
          title: 'Browser',
          fields: [
            ['User Agent', navigator.userAgent],
            ['Time zone', Intl.DateTimeFormat().resolvedOptions().timeZone]
          ]
        }
      ];
    } else {
      model.value.results[kind] = result;
      if (kind === 'clear_sidebar') emit('navigation-cleared');
    }
  } catch (error) {
    stopped = true;
    if (id === generation) {
      if (kind === 'info') {
        model.value.sections = [];
        model.value.error = error.message;
      } else model.value.results[kind] = { error: error.message };
    }
  } finally {
    if (id === generation) {
      model.value.busy = false;
      model.value.pending = '';
    }
  }
}
async function event(action) {
  if (model.value.busy) return;
  if (action.type === 'refresh') return refresh();
  if (
    action.type === 'field' &&
    ['sender', 'recipients', 'scriptPath', 'includeInternal'].includes(
      action.field
    )
  )
    model.value[action.field] = action.value;
  if (action.type === 'openLink') return openLink(action.url);
  if (action.type === 'test') {
    if (action.name !== 'links') return run(action.name, action.plan);
    const links = model.value.includeInternal
      ? model.value.internalLinks
      : model.value.links;
    const opened = links.filter((link) => openLink(link.url)).length;
    model.value.results.links = {
      opened,
      total: links.length,
      blocked: opened < links.length
    };
  }
  if (action.type === 'copy') {
    try {
      await copyText(UI.report(model.value, appearance.language));
    } catch {
      model.value.error = 'Clipboard access failed';
    }
  }
}
function openLink(value) {
  const allowed = [...model.value.links, ...model.value.internalLinks].some(
    (link) => link.url === value
  );
  if (!allowed || !value.startsWith('/projects/')) return false;
  const address = new URL(value, location.origin);
  if (address.origin !== location.origin) return false;
  const page = window.open(address.href, '_blank');
  if (page) page.opener = null;
  return !!page;
}
function open() {
  clear();
  dialog.value.show();
  return refresh();
}
defineExpose({ open });
</script>
<template>
  <AppDialog
    ref="dialog"
    title="System Info"
    window-kind="system_info"
    class="system-info-dialog"
    :close-on-outside="false"
    @closed="clear"
  >
    <div ref="host" class="system-info-body">
      <FrameView :scene="scene" @event="event" />
    </div>
  </AppDialog>
</template>
<style>
.system-info-dialog {
  width: min(800px, var(--dialog-owner-width, 96vw));
  height: min(680px, var(--dialog-owner-height, 94dvh));
}
.system-info-body {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
  background: var(--page);
}
.system-info-dialog > .app-dialog-content {
  padding: 0;
}
.system-info-body > .frame-view {
  position: absolute;
  inset: 0;
}
</style>
