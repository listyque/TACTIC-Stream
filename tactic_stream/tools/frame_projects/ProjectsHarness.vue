<script setup>
import { nextTick, onMounted, ref } from 'vue';
import { appearance } from '../../frontend/src/appearance.js';
import ProjectChooser from '../../frontend/src/features/projects/ProjectChooser.vue';
import ProjectCard from '../../frontend/src/features/projects/ProjectCard.vue';
import WorkspaceTabVisual from '../../frontend/src/controls/WorkspaceTabVisual.vue';
import WorkspaceTabs from '../../frontend/src/controls/WorkspaceTabs.vue';
import SectionTabRail from '../../frontend/src/controls/SectionTabRail.vue';
const railGeneration = ref(0);
const sections = ref([
    { id: 'assets', title: 'Assets', accent: '#6f9fc1', icon: 'assets' },
    { id: 'shots', title: 'Shots', accent: '#9f80c1', icon: 'movie' }
  ]),
  sectionSelected = ref('assets'),
  sectionCalls = ref(0),
  sectionReorders = ref([]);
const kind = ref('chooser'),
  selected = ref('one'),
  calls = ref(0),
  record = ref({}),
  state = ref({}),
  tabRecords = ref([
    { id: 'a', title: 'Assets' },
    { id: 'b', title: 'Second search' },
    { id: 'c', title: 'Long third search' }
  ]),
  current = ref('a');
const projects = [
  {
    code: 'one',
    title: 'Project one',
    description: 'Short description',
    category: 'Production',
    type: 'classic'
  },
  {
    code: 'two',
    title: 'Project two',
    description:
      'A much longer description that should wrap into several lines in a narrow project card with lots of extra data',
    category: 'Production',
    type: 'classic'
  },
  {
    code: 'empty',
    title: 'Without category',
    description: '',
    category: '',
    type: ''
  },
  {
    code: 'retired',
    title: 'Archived project',
    s_status: 'retired',
    description: 'Archived description',
    category: 'Production',
    type: 'classic'
  },
  {
    code: 'template',
    title: 'Template project',
    is_template: true,
    category: 'Templates',
    type: 'classic'
  },
  {
    code: 'builtin',
    title: 'Built-in project',
    __builtin__: true,
    category: 'System',
    type: 'admin'
  }
];
function selectedProject(code) {
  selected.value = code;
  calls.value++;
}
onMounted(() => {
  window.projectsHarness = {
    projects,
    get sections() {
      return sections.value;
    },
    get sectionCalls() {
      return sectionCalls.value;
    },
    get sectionReorders() {
      return sectionReorders.value;
    },
    get sectionSelected() {
      return sectionSelected.value;
    },
    replaceSections(records) {
      sections.value = records;
    },
    resetSections(count = 3) {
      sections.value = Array.from({ length: count }, (_, i) => ({
        id: 'section' + i,
        title: 'Section ' + i,
        accent: i % 2 ? '#9f80c1' : '#6f9fc1',
        icon: i % 2 ? 'movie' : 'assets'
      }));
      sectionSelected.value = 'section0';
      sectionCalls.value = 0;
      sectionReorders.value = [];
    },
    get calls() {
      return calls.value;
    },
    get current() {
      return current.value;
    },
    async configure(nextKind, style, language, long = false, tabState = {}) {
      kind.value = nextKind;
      if (nextKind === 'rail') {
        railGeneration.value++;
        sectionSelected.value = 'assets';
      }
      Object.assign(appearance, {
        theme: style,
        language,
        mode: language === 'en' ? 'dark' : 'light'
      });
      record.value = {
        ...projects[long ? 1 : 0],
        initials: long ? 'PT' : 'PO',
        projectType: 'classic'
      };
      state.value = tabState;
      await nextTick();
      if (nextKind === 'chooser')
        document.querySelector('#project-chooser').showPopover();
      await nextTick();
    },
    setTabs(value) {
      tabRecords.value = value;
    },
    get tabs() {
      return tabRecords.value;
    }
  };
});
</script>
<template>
  <ProjectChooser
    v-if="kind === 'chooser'"
    :projects="projects"
    :selected="selected"
    @selected="selectedProject"
  />
  <ProjectChooser
    v-else-if="kind === 'inline'"
    inline
    :projects="projects"
    :selected="selected"
    @selected="selectedProject"
  />
  <ProjectCard
    v-else-if="kind === 'card'"
    style="width: 248px"
    :record="record"
    :selected="!!state.current"
    @selected="selectedProject"
  />
  <div
    v-else-if="kind === 'tab'"
    style="position: relative; width: 180px; height: 50px"
  >
    <WorkspaceTabVisual
      :record="{
        title: 'Assets',
        current: !!state.current,
        closable: true,
        dirty: !!state.dirty
      }"
      :hovered="!!state.hovered"
    />
  </div>
  <div
    v-else-if="kind === 'rail'"
    style="width: 400px; height: 260px; position: relative"
  >
    <SectionTabRail
      :key="railGeneration"
      class="workspace-rail"
      style="height: 260px"
      :tabs="sections"
      :selected="sectionSelected"
      @select="
        sectionSelected = $event;
        sectionCalls++;
      "
      @close="
        sections = sections.filter((tab) => tab.id !== $event);
        sectionSelected = sections[0]?.id || '';
      "
      @reorder="
        (source, target) => {
          sectionReorders.push([source, target]);
          const [tab] = sections.splice(source, 1);
          sections.splice(target, 0, tab);
        }
      "
    />
  </div>
  <WorkspaceTabs
    v-else
    :tabs="tabRecords"
    :selected="current"
    style="width: 640px"
    @select="current = $event"
    @close="
      tabRecords = tabRecords.filter((tab) => tab.id !== $event);
      if (current === $event) current = tabRecords[0]?.id || '';
    "
    @reorder="
      (a, b) => {
        const [tab] = tabRecords.splice(a, 1);
        tabRecords.splice(b, 0, tab);
      }
    "
  />
</template>
<style>
body {
  margin: 0;
  background: var(--page);
}
#app {
  min-height: 100vh;
}
</style>
