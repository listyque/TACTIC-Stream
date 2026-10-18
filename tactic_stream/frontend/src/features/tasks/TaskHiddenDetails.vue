<script setup>
import {
  computed,
  nextTick,
  ref,
  watch,
  markRaw,
  h,
  onBeforeUnmount
} from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppTextArea from '../../controls/AppTextArea.vue';
import TaskDetailValue from './TaskDetailValue.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/details.ui.mjs';
const props = defineProps({ editor: Object, columns: Array, busy: Boolean });
const emit = defineEmits(['change', 'milestones']);
let descriptionBaseline = '';
const description = ref(''),
  editing = ref(false),
  area = ref(null);
const fields = computed(() => {
  const visible = (key) =>
    props.columns.some((column) => column.key === key && column.visible);
  const order = [
    'process',
    'context',
    'status',
    'assigned',
    'bid_start_date',
    'bid_end_date',
    'progress',
    'completion',
    'bid_duration',
    'priority',
    'milestone_code',
    'supervisor'
  ];
  return order.flatMap((name) => {
    const field = props.editor?.fields.find((field) => field.name === name);
    const key = name.endsWith('_date')
      ? 'dates'
      : name === 'completion'
        ? 'progress'
        : name;
    return field &&
      (['process', 'context'].includes(name)
        ? props.editor.plans[0].operation === 'create'
        : ['priority', 'milestone_code', 'supervisor'].includes(name) ||
          visible(key))
      ? [field]
      : [];
  });
});
const descriptionField = computed(() =>
  props.editor?.fields.find((field) => field.name === 'description')
);
const creating = computed(() => props.editor?.plans[0].operation === 'create');
watch(
  () => props.editor?.values.description,
  (value) => {
    if (!editing.value) description.value = value || '';
  },
  { immediate: true }
);
watch(
  creating,
  (value) => {
    editing.value = !!value;
  },
  { immediate: true }
);
function finish() {
  if (
    !props.busy &&
    descriptionField.value?.editable &&
    description.value !== (props.editor.values.description || '')
  )
    emit('change', 'description', description.value);
  editing.value = creating.value;
}
async function editDescription() {
  if (editing.value) {
    finish();
    area.value?.$el.blur();
  } else {
    descriptionBaseline = description.value;
    editing.value = true;
    await nextTick();
    area.value?.focus();
  }
}
function escape(event) {
  description.value = descriptionBaseline;
  emit('change', 'description', descriptionBaseline);
  editing.value = creating.value;
  event.target.blur();
}

const host = ref(null),
  width = ref(0);
const scene = computed(() =>
  UI.describe(
    {
      fields: fields.value.map((field) => ({
        name: field.name,
        value: props.editor?.values[field.name]
      })),
      progress: Number(
        props.editor?.values.progress ?? props.editor?.values.completion ?? 0
      ),
      description: !!descriptionField.value,
      descriptionEditable: !!descriptionField.value?.editable,
      creating: creating.value,
      editingDescription: editing.value,
      busy: props.busy
    },
    width.value,
    appearance.language
  )
);
const fieldComponent = markRaw(TaskDetailValue);
const descriptionComponent = markRaw({
  setup(_, { attrs }) {
    return () =>
      h(
        'div',
        {
          ...attrs,
          'data-task-field': 'description',
          class: 'task-description-value'
        },
        [
          h(AppTextArea, {
            ref: area,
            modelValue: description.value,
            label: 'Description',
            placeholder: 'Add task description…',
            readonly: !editing.value,
            disabled: props.busy || !descriptionField.value?.editable,
            style: { paddingRight: creating.value ? '12px' : '42px' },
            'onUpdate:modelValue': (value) => {
              description.value = value;
              if (
                editing.value &&
                !props.busy &&
                descriptionField.value?.editable
              )
                emit('change', 'description', value);
            },
            onFocus: () => {
              descriptionBaseline = description.value;
            },
            onBlur: finish,
            onKeydown: (event) => {
              if (event.key === 'Escape') {
                event.preventDefault();
                escape(event);
              }
            }
          })
        ]
      );
  }
});
const views = computed(() =>
  Object.assign(
    { description: { component: descriptionComponent } },
    Object.fromEntries(
      fields.value.map((field) => [
        field.name,
        {
          component: fieldComponent,
          props: {
            field,
            editor: props.editor,
            busy: props.busy,
            onChange: (value) => emit('change', field.name, value),
            onMilestones: () => emit('milestones')
          }
        }
      ])
    )
  )
);
let observer;
watch(
  host,
  (element) => {
    observer?.disconnect();
    if (!element) return;
    const measure = () => {
      width.value = frameContentWidth(element);
    };
    measure();
    observer = observeFrameSizes(measure);
    observer.observe(element);
  },
  { flush: 'post' }
);
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <section
    v-if="editor"
    ref="host"
    class="task-workspace-details"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" :views="views" @event="editDescription" />
  </section>
</template>
<style>
.task-workspace-details {
  padding: 0;
  border: 0;
}
.task-description-value > .app-text-area {
  width: 100%;
  height: 100%;
  min-height: 0;
  resize: none;
  font-size: var(--text-label);
}
</style>
