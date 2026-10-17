<script setup>
// ConfigurationProjectPage.qml: catalogue, explicit activation, edit, template and creation.
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
import { projectCatalog, rpc } from '../../api.js';
import { t } from '../../i18n.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/projects/catalog.ui.mjs';
import ProjectCreation from '../projects/ProjectCreation.vue';
import RecordForm from '../objects/RecordForm.vue';
import ProjectEditorSurface from '../projects/ProjectEditorSurface.vue';
const props = defineProps({
  ticket: String,
  project: String,
  canAdminister: Boolean,
  openProject: Function
});
const emit = defineEmits(['changed', 'help']);
const projects = ref([]),
  selected = ref(''),
  editor = ref(null),
  creator = ref(null),
  busy = ref(false),
  error = ref('');
const item = computed(() =>
  projects.value.find((item) => item.code === selected.value)
);
const editable = computed(
  () =>
    props.canAdminister && item.value && !item.value.__builtin__ && !busy.value
);
const host = ref(null),
  viewport = ref({ width: 900, height: 600 }),
  filters = ref({ retired: false, templates: false, builtins: false });
const records = computed(() =>
  projects.value.map((record) => ({
    ...record,
    isBuiltin: !!record.__builtin__,
    isTemplate: [true, 1, 'true', 't', '1'].includes(record.is_template),
    isRetired: record.s_status === 'retired',
    preview: record.preview || record.__preview__ || ''
  }))
);
const visible = computed(() =>
  UI.visibleProjects(records.value, filters.value).map((projectDetails) => ({
    projectCode: projectDetails.code,
    projectDetails
  }))
);
const model = computed(() => ({
  counts: {
    retired: records.value.filter((item) => item.isRetired).length,
    templates: records.value.filter((item) => item.isTemplate).length,
    builtins: records.value.filter((item) => item.isBuiltin).length
  },
  totalCount: records.value.length,
  visibleCount: visible.value.length,
  selected: records.value.find((record) => record.code === selected.value),
  currentCode: props.project,
  currentTitle: projects.value.find((record) => record.code === props.project)
    ?.title,
  canManage: props.canAdminister,
  busy: busy.value,
  error: error.value,
  filters: filters.value
}));
const scene = computed(() =>
  UI.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const row = (list, record) =>
  UI.row(model.value, record, list.width - 16, appearance.language);
let observer;
let generation = 0;
watch(
  () => props.ticket,
  () => {
    generation++;
    projects.value = [];
    selected.value = '';
    busy.value = false;
    error.value = '';
  }
);
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => {
  generation++;
  observer?.disconnect();
});
function dispatch(action) {
  if (action.type === 'select') selected.value = action.record.code;
  else if (action.type === 'filter') filters.value[action.field] = action.value;
  else if (action.type === 'activate') activate(action.code);
  else if (action.type === 'deactivate') activate('');
  else if (action.type === 'edit') editor.value.open(item.value.__search_key__);
  else if (action.type === 'archive') archive();
  else if (action.type === 'create') creator.value.open();
  else if (action.type === 'refresh') load();
}
async function load() {
  const request = generation;
  busy.value = true;
  error.value = '';
  try {
    const records = await projectCatalog(props.ticket);
    if (request === generation) projects.value = records;
  } catch (failure) {
    if (request !== generation) return;
    error.value = failure.message;
  } finally {
    if (request === generation) busy.value = false;
  }
}
async function activate(code) {
  const request = generation;
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    if ((await props.openProject(code)) === false)
      error.value = 'The project could not be activated.';
  } catch (failure) {
    if (request !== generation) return;
    error.value = failure.message;
  } finally {
    if (request === generation) busy.value = false;
  }
}
async function changed() {
  await load();
  emit('changed');
}
async function created(code) {
  if ((await props.openProject(code)) === false)
    throw new Error('The project could not be activated.');
  selected.value = code;
  await changed();
}
async function archive() {
  const request = generation;
  if (!editable.value) return;
  busy.value = true;
  error.value = '';
  try {
    const result = await rpc('execute_cmd', [
      { ticket: props.ticket, project: 'admin', language: 'python' },
      'tactic.ui.app.ProjectTemplateExportCmd',
      { project_code: item.value.code }
    ]);
    if (request !== generation) return;
    const link = document.createElement('a');
    link.href =
      '/assets/_cache/' +
      encodeURIComponent(props.ticket) +
      '/' +
      encodeURIComponent(result.info.filename);
    link.download = result.info.filename;
    link.click();
  } catch (failure) {
    if (request !== generation) return;
    error.value = failure.message;
  } finally {
    if (request === generation) busy.value = false;
  }
}
onMounted(load);
</script>
<template>
  <section ref="host" class="configuration-projects-frame" :aria-busy="busy">
    <FrameView
      :scene="scene"
      :models="{ projects: visible }"
      :describe-row="row"
      @event="dispatch"
    />
    <RecordForm
      ref="editor"
      class="configuration-project-editor"
      :ticket="ticket"
      project="admin"
      search-type="sthpw/project"
      edit-view="configuration_edit"
      modal
      @saved="changed"
      ><template
        #surface="{
          form,
          save,
          cancel,
          close,
          keep,
          reportError,
          contextValid
        }"
        ><ProjectEditorSurface
          v-if="form.definition || form.error"
          :form="form"
          :preview-url="typeof item?.preview === 'string' ? item.preview : ''"
          :context-valid="contextValid"
          @save="save"
          @cancel="cancel"
          @close="close"
          @keep="keep"
          @error="reportError"
          @help="$emit('help', 'project_creation')"
        />
        <p v-else role="status">{{ t('Loading data…') }}</p></template
      ></RecordForm
    >
    <ProjectCreation ref="creator" :ticket="ticket" :open-project="created" />
  </section>
</template>
<style>
.configuration-projects-frame {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.configuration-projects-frame > .frame-view {
  position: absolute;
  inset: 0;
}
.configuration-project-editor {
  width: 900px;
  height: min(850px, calc(100dvh - 32px));
  padding: 0;
  overflow: hidden;
}
</style>
