<script setup>
// Handler DescriptionEditor.qml / state_detail_editing.py (EPL-1.0).
import {
  computed,
  inject,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch
} from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import DescriptionSurface from './DescriptionSurface.vue';
import { linkifyPlainText } from '../../controls/richText.js';
import { browserLink } from '../workspace/links.js';
const props = defineProps({ ticket: String, project: String, target: Object });
const emit = defineEmits(['saved', 'session-expired']);
const openObjectTab = inject('openObjectTab', null);
const drafts = reactive(new Map()),
  current = ref(''),
  pinned = ref(null),
  editor = ref(null);
const entry = computed(() => drafts.get(current.value));
const pinActive = computed(() => pinned.value?.project === props.project);
const value = computed({
  get() {
    if (pinActive.value) return pinned.value.value;
    if (!entry.value) return '';
    return entry.value.editing || entry.value.saving
      ? entry.value.value
      : entry.value.original;
  },
  set(text) {
    if (pinActive.value) pinned.value.value = text;
    else if (entry.value) entry.value.value = text;
  }
});
const dirty = computed(
  () => !!entry.value && entry.value.value !== entry.value.original
);
const retained = computed(() =>
  [...drafts.entries()].filter(
    ([, item]) => item.project === props.project && item.value !== item.original
  )
);
const html = computed(() =>
  linkifyPlainText(value.value, (link) => browserLink(link, props.project))
);
const frameModel = computed(() => ({
  value: value.value,
  enabled: !!entry.value && !entry.value.saving,
  editing: !!entry.value?.editing,
  pinned: pinActive.value,
  dirty: dirty.value,
  saving: !!entry.value?.saving,
  canSave: !!entry.value?.searchKey,
  error: entry.value?.error || '',
  title: entry.value?.title || '',
  kind: entry.value?.kind || '',
  header: false,
  current: current.value,
  drafts:
    retained.value.length > 1 ||
    retained.value.some(
      ([key]) =>
        key !== current.value ||
        (!entry.value?.editing && !entry.value?.saving && !pinActive.value)
    )
      ? retained.value.map(([key, item]) => ({ value: key, label: item.title }))
      : []
}));
function dispatch(action) {
  if (action.type === 'edit') edit();
  else if (action.type === 'cancel') discard();
  else if (action.type === 'save') save();
  else if (action.type === 'pin') pin();
  else if (action.type === 'unpin') unpin();
  else if (action.type === 'draft') resumeDraft(action.value);
}
function activateLink(event) {
  const link = event.target.closest('[data-rich-link]')?.dataset.richLink;
  if (
    link &&
    openObjectTab &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.altKey &&
    !event.button
  ) {
    event.preventDefault();
    openObjectTab(link, props.project);
  }
}
watch(
  () => [props.target, props.project],
  () => {
    const target = props.target;
    if (!target || target.project !== props.project) {
      current.value = '';
      return;
    }
    const key = target.project + ':' + target.id;
    let item = drafts.get(key);
    const original = String(
      target.record?.description || target.record?.detail || ''
    );
    if (!item) {
      item = {
        ...target,
        original,
        value: original,
        editing: false,
        saving: false,
        error: ''
      };
      drafts.set(key, item);
    } else {
      item.title = target.title;
      if (!item.saving && item.value === item.original)
        item.value = item.original = original;
    }
    current.value = key;
  },
  { immediate: true }
);
function edit() {
  entry.value.editing = true;
  nextTick(() => editor.value?.focus());
}
function resumeDraft(key) {
  current.value = key;
  if (pinActive.value) pinned.value = null;
  edit();
}
function discard() {
  entry.value.value = entry.value.original;
  entry.value.editing = false;
  entry.value.error = '';
}
function pin() {
  pinned.value = { project: props.project, value: value.value };
  discard();
}
function unpin() {
  pinned.value = null;
  if (entry.value) {
    entry.value.editing = false;
    entry.value.error = '';
  }
}
async function save() {
  const item = entry.value;
  if (!item?.searchKey || item.saving || item.value === item.original) return;
  const text = item.value,
    ticket = props.ticket;
  item.saving = true;
  item.editing = false;
  item.error = '';
  try {
    await rpc('update', [
      { ticket, project: item.project },
      item.searchKey,
      { description: text }
    ]);
    item.original = text;
    item.editing = false;
    item.record.description = text;
    emit('saved', item.searchKey, text);
  } catch (failure) {
    item.editing = true;
    item.error =
      failure instanceof TypeError
        ? 'Unable to reach the server.'
        : failure.message;
    if (failure.code === 'authentication_failed') emit('session-expired');
  } finally {
    item.saving = false;
  }
}
function canLeave() {
  return (
    ![...drafts.values()].some((item) => item.saving) &&
    (![...drafts.values()].some((item) => item.value !== item.original) ||
      window.confirm(t('Discard unsaved descriptions?')))
  );
}
function beforeUnload(event) {
  if (
    [...drafts.values()].some(
      (item) => item.saving || item.value !== item.original
    )
  ) {
    event.preventDefault();
    event.returnValue = '';
  }
}
onMounted(() => window.addEventListener('beforeunload', beforeUnload));
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload));
defineExpose({
  canLeave,
  pinnedValue: () => (pinActive.value ? pinned.value.value : '')
});
</script>
<template>
  <Teleport defer to="#dock-description">
    <section
      class="description-editor"
      :aria-label="t('Description editor')"
      @keydown.esc="entry?.editing && !entry.saving && discard()"
    >
      <DescriptionSurface
        ref="editor"
        :model="frameModel"
        :text="value"
        :html="html"
        @value="value = $event"
        @link="activateLink"
        @event="dispatch"
      />
    </section>
  </Teleport>
</template>
<style scoped>
.description-editor {
  height: 100%;
  min-height: 0;
  background: var(--surface);
}
</style>
