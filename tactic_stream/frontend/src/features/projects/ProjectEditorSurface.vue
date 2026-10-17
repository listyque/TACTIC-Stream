<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import ImagePicker from '../../controls/ImagePicker.vue';
import { fieldKind, unsupportedField } from '../objects/recordFields.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/projects/editor.ui.mjs';
const props = defineProps({
  form: Object,
  contextValid: Boolean,
  previewUrl: String
});
const emit = defineEmits(['save', 'cancel', 'close', 'keep', 'help', 'error']);
const imageValidating = ref(false);
const host = ref(null),
  viewport = ref({ width: 800, height: 700 });
const known = [
  'snapshot',
  'code',
  'title',
  'category',
  'type',
  'description',
  's_status',
  'is_template'
];
const inputFields = computed(() => props.form.definition?.fields || []);
const imageField = computed(() =>
  inputFields.value.find((field) => fieldKind(field) === 'FileInput')
);
const options = (field) =>
  field?.choices?.map((value, index) => ({
    value,
    label: field.labels[index],
    dataLabel: true
  }));
const unsupported = computed(() =>
  inputFields.value.filter(
    (field) =>
      unsupportedField(field) ||
      (!known.includes(field.name) &&
        ![
          'TextWdg',
          'TextAreaWdg',
          'SelectWdg',
          'CheckboxWdg',
          'HiddenWdg'
        ].includes(fieldKind(field)))
  )
);
const extraFields = computed(() =>
  inputFields.value
    .filter(
      (field) =>
        !known.includes(field.name) &&
        fieldKind(field) !== 'HiddenWdg' &&
        !unsupported.value.includes(field)
    )
    .map((field) => ({
      kind:
        fieldKind(field) === 'SelectWdg'
          ? 'Choice'
          : fieldKind(field) === 'TextAreaWdg'
            ? 'Area'
            : fieldKind(field) === 'CheckboxWdg'
              ? 'Switch'
              : 'Field',
      field: field.name,
      title: field.title,
      description: field.options.hint || field.options.hint_text || '',
      dataLabel: true,
      options: options(field),
      readOnly: !!field.input?.read_only || field.options.read_only === 'true'
    }))
);
const model = computed(() => ({
  values: {
    ...props.form.draft,
    archived: props.form.draft.s_status === 'retired',
    isTemplate: [true, 1, '1', 'true', 't'].includes(
      props.form.draft.is_template
    )
  },
  stagedImage: !!(imageField.value && props.form.files[imageField.value.name]),
  typeOptions: options(
    inputFields.value.find((field) => field.name === 'type')
  ),
  extraFields: extraFields.value,
  busy: props.form.saving || imageValidating.value,
  loading: props.form.loading,
  uncertain: props.form.uncertain,
  dirty:
    JSON.stringify(props.form.draft) !== JSON.stringify(props.form.baseline),
  blocked: !props.contextValid || unsupported.value.length > 0,
  notice: unsupported.value.length
    ? 'This form contains unsupported inputs or options. Saving is unavailable.'
    : '',
  error: props.form.error,
  discard: props.form.discard,
  style: appearance.theme
}));
const scene = computed(() =>
  UI.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const views = computed(() => ({
  image: {
    component: ImagePicker,
    props: {
      previewSize: 160,
      inlineErrors: false,
      onError: (message) => emit('error', message),
      onValidating: (value) => {
        imageValidating.value = value;
      },
      previewUrl: props.previewUrl,
      statusText:
        imageField.value && props.form.files[imageField.value.name]
          ? 'A new preview is ready to be queued'
          : 'Current project preview',
      description:
        'Choose a large image; the repository web representation is used automatically when available.',
      modelValue: imageField.value
        ? props.form.files[imageField.value.name]
        : null,
      fallbackText: String(props.form.draft.code || '')
        .slice(0, 2)
        .toUpperCase(),
      disabled:
        !imageField.value ||
        props.form.saving ||
        model.value.blocked ||
        model.value.uncertain,
      'onUpdate:modelValue': (file) => {
        const key = imageField.value.name;
        if (file) props.form.files[key] = file;
        else delete props.form.files[key];
        props.form.draft[key] = file?.name || '';
      }
    }
  }
}));
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function dispatch(action) {
  if (action.type === 'field')
    props.form.draft[
      { archived: 's_status', isTemplate: 'is_template' }[action.field] ||
        action.field
    ] =
      action.field === 'archived'
        ? action.value
          ? 'retired'
          : ''
        : action.value;
  else if (action.type === 'keep') emit('keep');
  else if (action.type === 'discard') emit('close');
  else if (action.type === 'close') emit('cancel');
  else if (action.type === 'save' && !imageValidating.value) emit('save');
  else if (action.type === 'help') emit('help');
}
</script>
<template>
  <div ref="host" class="project-editor-frame">
    <FrameView :scene="scene" :views="views" @event="dispatch" />
  </div>
</template>
<style>
.project-editor-frame {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.project-editor-frame > .frame-view {
  position: absolute;
  inset: 0;
}
</style>
