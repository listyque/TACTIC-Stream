<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { rpc } from '../../api.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/views.ui.mjs';

const props = defineProps({
  ticket: String,
  project: String,
  searchType: String,
  current: String
});
const emit = defineEmits(['use', 'configure', 'changed']);
const dialog = ref(null),
  host = ref(null),
  ui = ref(UI.initial());
const model = ref({ views: [], busy: false, error: '', uncertain: false });
const size = ref({ width: 900, height: 590 });
let observer,
  generation = 0,
  context;
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
const scene = computed(() =>
  UI.describe(
    model.value,
    ui.value,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
watch(
  () => [props.ticket, props.project, props.searchType],
  () => {
    generation++;
    dialog.value?.close();
    context = null;
  }
);
onBeforeUnmount(() => {
  generation++;
  observer?.disconnect();
});
async function call(command) {
  if (!context || model.value.busy) return;
  const id = ++generation,
    captured = { ...context };
  model.value = { ...model.value, busy: true, error: '' };
  try {
    const result = await rpc(
      'execute_cmd',
      [
        { ticket: captured.ticket, project: captured.project },
        'tactic.ui.table.views.TableViewsCmd',
        {
          search_type: captured.searchType,
          current: model.value.current || captured.current,
          ...command
        }
      ],
      {},
      true
    );
    if (id !== generation) return;
    if (result.status !== 'OK')
      throw Error(result.description || 'Table views could not be loaded');
    let info =
      typeof result.info === 'string' ? JSON.parse(result.info) : result.info;
    if (command.action !== 'read') {
      const fresh = await rpc(
        'execute_cmd',
        [
          { ticket: captured.ticket, project: captured.project },
          'tactic.ui.table.views.TableViewsCmd',
          {
            search_type: captured.searchType,
            current: info.current,
            action: 'read'
          }
        ],
        {},
        true
      );
      if (id !== generation) return;
      if (fresh.status !== 'OK')
        throw Error(fresh.description || 'Table views could not be loaded');
      info = {
        ...(typeof fresh.info === 'string'
          ? JSON.parse(fresh.info)
          : fresh.info),
        selected: info.selected
      };
    }
    model.value = { ...info, busy: false, error: '', uncertain: false };
    ui.value = UI.loaded(ui.value, model.value);
    if (command.action !== 'read') emit('changed', info);
  } catch (error) {
    if (id === generation)
      model.value = {
        ...model.value,
        busy: false,
        error: error.message,
        uncertain: command.action !== 'read'
      };
  }
}
function event(action) {
  const next = UI.transition(ui.value, model.value, action);
  ui.value = next.ui;
  if (!next.command) return;
  const command = next.command;
  if (command.action === 'use' || command.action === 'configure') {
    emit(command.action, command.view);
    dialog.value.close();
  } else call(command);
}
async function open() {
  context = {
    ticket: props.ticket,
    project: props.project,
    searchType: props.searchType,
    current: props.current || 'table'
  };
  ui.value = UI.initial();
  ui.value.selected = context.current;
  model.value = {
    views: [],
    busy: false,
    error: '',
    uncertain: false,
    ...context
  };
  dialog.value.show();
  await call({ action: 'read' });
}
defineExpose({ open });
</script>
<template>
  <AppDialog
    ref="dialog"
    title="Table views manager"
    window-kind="table_views"
    class="table-views-manager"
    :close-on-outside="false"
    :close-on-escape="!model.busy"
    @closed="generation++"
  >
    <div ref="host" class="table-views-manager-body">
      <FrameView
        :scene="scene"
        :models="{ views: UI.rows(model, ui) }"
        :describe-row="
          (list, record) => UI.row(list, record, ui, model, appearance.language)
        "
        @event="event"
      />
    </div>
  </AppDialog>
</template>
<style>
.table-views-manager {
  width: min(960px, var(--dialog-owner-width, 96vw));
  height: min(720px, var(--dialog-owner-height, 94dvh));
}
.table-views-manager-body {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
}
.table-views-manager > .app-dialog-content {
  padding: 0;
}
.table-views-manager-body > .frame-view {
  position: absolute;
  inset: 0;
}
</style>
