<script setup>
import { computed, ref, markRaw, h, nextTick } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import AppMenu from '../../frontend/src/controls/AppMenu.vue';
import AppMenuItem from '../../frontend/src/controls/AppMenuItem.vue';
import BusyIndicator from '../../frontend/src/controls/BusyIndicator.vue';
import AppSlider from '../../frontend/src/controls/AppSlider.vue';
import * as Catalog from '../../src/tactic_stream/shared_ui/controls/catalog.ui.mjs';
import { appearance } from '../../frontend/src/appearance.js';

const model = ref(Catalog.initial());
const state = ref('idle');
const viewport = ref({ width: 900, height: 900 });
const view = ref(null);
const cells = Array.from({ length: 50 }, () => [{}, {}, {}]);
const models = computed(() => ({
  cells,
  treeRows: Catalog.treeRows(model.value)
}));
const scene = computed(() =>
  Catalog.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language,
    state.value
  )
);
const enabled = computed(() => !['disabled', 'loading'].includes(state.value));
const menuProps = computed(() => ({
  label: 'Actions',
  showLabel: false,
  disabled: !enabled.value,
  overlay: true,
  width: 244
}));
const Menu = {
  components: { AppMenu, AppMenuItem },
  props: ['options', 'disabled'],
  emits: ['event']
};
// The runtime-only Vue build uses these normal render functions for named bricks.
Menu.render = function () {
  return h(
    AppMenu,
    {
      class: 'catalog-menu',
      label: 'Actions',
      compactTrigger: true,
      disabled: this.disabled,
      overlay: true,
      width: 244
    },
    () =>
      this.options.map((item) =>
        h(AppMenuItem, {
          key: item.command,
          label: item.title,
          icon: item.icon,
          translate: false,
          onClick: () => this.$emit('event', { type: item.command })
        })
      )
  );
};
const Busy = {
  props: ['running'],
  render() {
    return h('div', { style: 'display:flex;align-items:center;' }, [
      h(BusyIndicator, { running: this.running })
    ]);
  }
};
function event(action) {
  model.value = Catalog.transition(model.value, action);
  if (action.type === 'treeKey')
    nextTick(() => view.value.focusControl('tree_' + model.value.treeSelected));
}
function row(list, record) {
  return Catalog.row(
    list,
    record,
    model.value,
    appearance.language,
    state.value
  );
}
const views = computed(() => ({
  menu: {
    component: markRaw(Menu),
    props: {
      ...menuProps.value,
      options: Catalog.menuActions(appearance.language),
      onEvent: event
    }
  },
  busy: {
    component: markRaw(Busy),
    props: { running: state.value === 'loading' }
  },
  slider: {
    component: markRaw(AppSlider),
    props: { label: 'Size', disabled: !enabled.value, modelValue: 50 }
  }
}));
window.frameControls = {
  configure(options) {
    if (options.state) state.value = options.state;
    if (options.width)
      viewport.value = { width: options.width, height: options.height || 900 };
    if (options.language) appearance.language = options.language;
    if (options.theme) appearance.theme = options.theme;
    if (options.mode) appearance.mode = options.mode;
  },
  reset() {
    model.value = Catalog.initial();
  },
  get model() {
    return model.value;
  },
  get scene() {
    return scene.value;
  },
  focus(name) {
    return view.value.focusControl(name);
  }
};
</script>
<template>
  <FrameView
    ref="view"
    :scene="scene"
    :models="models"
    :views="views"
    :describe-row="row"
    :describe-cell="Catalog.cell"
    @event="event"
  />
</template>
<style>
.catalog-menu > summary {
  width: auto;
  height: 100%;
  aspect-ratio: 1;
}
</style>
