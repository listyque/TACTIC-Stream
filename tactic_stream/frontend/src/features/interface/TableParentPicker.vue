<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { tableParentGroup } from '../../api.js';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { translate } from '../../../../src/tactic_stream/shared_ui/core/strings.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/table/parent.state.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/parent.ui.mjs';

const props = defineProps({ ticket: String, project: String });
const emit = defineEmits(['saved']);
const panel = ref(null),
  body = ref(null),
  frame = ref(null),
  opened = ref(false);
const state = ref(State.create({}));
const size = ref({ width: 360, height: 480 });
const records = computed(() => State.rows(state.value));
let generation = 0,
  pending,
  context,
  hostProject,
  anchor,
  observer,
  reposition;

function close() {
  generation++;
  pending?.abort();
  pending = null;
  opened.value = false;
  observer?.disconnect();
  observer = null;
  window.removeEventListener('resize', reposition);
  window.visualViewport?.removeEventListener('resize', reposition);
  reposition = null;
  panel.value?.hidePopover();
}

async function request(arguments_) {
  const current = generation,
    abort = new AbortController();
  pending = abort;
  const { projectCode, ...values } = arguments_;
  const valid = () =>
    current === generation &&
    opened.value &&
    context.ticket === props.ticket &&
    hostProject === props.project;
  try {
    const result = await tableParentGroup(context, values, abort.signal);
    if (valid()) {
      apply(State.accept(state.value, values.action, result.info));
      if (values.action === 'prepare')
        nextTick(() => {
          if (valid()) frame.value?.focusControl('parentQuery');
        });
    }
  } catch (error) {
    if (valid())
      apply(
        State.accept(
          state.value,
          values.action,
          null,
          error.message,
          values.action === 'save' &&
            ![400, 401, 403, 404, 409, 422].includes(error.status)
        )
      );
  } finally {
    if (pending === abort) pending = null;
  }
}

function apply(change) {
  state.value = change.state;
  if (change.request) request(change.request);
  else if (change.close) {
    const key = state.value.seed.targetSearchKey;
    close();
    if (change.saved) emit('saved', key);
  }
}

function activate(action) {
  apply(State.dispatch(state.value, action));
}

async function open(cell, sourceTitle, element) {
  if (opened.value) return;
  generation++;
  anchor = element;
  hostProject = props.project;
  context = {
    ticket: props.ticket,
    project: cell.projectCode || props.project,
    language: 'python'
  };
  state.value = State.create({
    ...cell,
    projectCode: context.project,
    sourceTitle
  });
  opened.value = true;
  const current = generation,
    currentAnchor = anchor;
  const valid = () => current === generation && opened.value;
  reposition = () => {
    if (!valid()) return;
    const viewport = window.visualViewport,
      width = Math.min(
        UI.popupMetrics.width,
        (viewport?.width || innerWidth) - 32
      ),
      height = Math.min(
        UI.popupMetrics.height,
        (viewport?.height || innerHeight) - 32
      );
    size.value = {
      width: width - UI.popupMetrics.padding * 2,
      height: Math.max(
        UI.popupMetrics.minimumBody,
        height - UI.popupMetrics.padding * 2
      )
    };
    if (!currentAnchor?.isConnected) return close();
    Object.assign(panel.value.style, {
      width: width + 'px',
      height: height + 'px'
    });
    const bounds = currentAnchor.getBoundingClientRect();
    panel.value.style.left =
      Math.max(16, Math.min(bounds.right - width, innerWidth - width - 16)) +
      'px';
    panel.value.style.top =
      Math.max(16, Math.min(bounds.bottom + 4, innerHeight - height - 16)) +
      'px';
  };
  await nextTick();
  if (!valid()) return;
  reposition();
  if (!valid()) return;
  panel.value.showPopover();
  window.addEventListener('resize', reposition);
  window.visualViewport?.addEventListener('resize', reposition);
  observer = observeFrameSizes((entries) => {
    if (!valid()) return;
    for (const entry of entries) {
      if (
        entry.target === anchor &&
        (!anchor.isConnected ||
          !entry.contentRect.width ||
          !entry.contentRect.height)
      )
        return close();
      if (entry.target === body.value)
        size.value = {
          width: entry.contentRect.width,
          height: entry.contentRect.height
        };
    }
  });
  observer.observe(body.value);
  observer.observe(anchor);
  apply(State.begin(state.value, 'prepare'));
}

watch(() => [props.ticket, props.project], close);
onBeforeUnmount(close);
defineExpose({ open, close });
</script>

<template>
  <Teleport to="body">
    <div
      ref="panel"
      popover="manual"
      class="frame-popup-surface table-parent-picker"
      role="dialog"
      :aria-label="translate('Change parent', appearance.language)"
      @keydown.esc.stop.prevent="activate({ type: 'cancel' })"
    >
      <div
        ref="body"
        class="table-parent-picker-body"
        :style="{ minHeight: UI.popupMetrics.minimumBody + 'px' }"
      >
        <FrameView
          v-if="opened"
          ref="frame"
          :scene="
            UI.describe(state, size.width, size.height, appearance.language)
          "
          :models="{ parentRows: records }"
          :describe-row="
            (list, row) =>
              UI.row(row, Math.max(0, list.width - 16), appearance.language)
          "
          @event="activate"
        />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.table-parent-picker {
  inset: auto;
  padding: 10px;
  max-height: min(520px, calc(100dvh - 32px));
  overflow: auto;
}
.table-parent-picker-body {
  position: relative;
  height: 100%;
  width: 100%;
}
</style>
