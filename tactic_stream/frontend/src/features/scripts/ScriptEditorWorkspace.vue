<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppSplitter from '../../controls/AppSplitter.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/editor.ui.mjs';

const props = defineProps({ model: { type: Object, required: true } });
const emit = defineEmits(['event']);
const host = ref(null),
  viewport = ref({ width: 0, height: 0 });
const bounds = computed(() =>
  UI.layout(props.model, viewport.value.width, viewport.value.height)
);
const toolbar = computed(() =>
  UI.toolbar(props.model, bounds.value.main.width, appearance.language)
);
const output = computed(() =>
  UI.outputToolbar(props.model, bounds.value.output.width, appearance.language)
);
const footer = computed(() =>
  UI.footer(props.model, bounds.value.main.width, appearance.language)
);
const side = computed(() =>
  UI.sideTabs(props.model, bounds.value.tree.width, appearance.language)
);
const style = (rect) => ({
  position: 'absolute',
  left: rect.x + 'px',
  top: rect.y + 'px',
  width: rect.width + 'px',
  height: rect.height + 'px'
});
let observer;
onMounted(() => {
  const measure = () => {
    viewport.value = {
      width: frameContentWidth(host.value),
      height: host.value.clientHeight
    };
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="script-editor-workspace">
    <div class="script-editor-main" :style="style(bounds.main)">
      <div class="script-editor-toolbar" :style="style(bounds.toolbar)">
        <FrameView
          :style="{ width: toolbar.contentWidth + 'px', height: '32px' }"
          :scene="toolbar"
          @event="emit('event', $event)"
        />
      </div>
      <div :style="style(bounds.tabs)"><slot name="tabs" /></div>
      <section
        class="script-editor-output"
        :class="{ wrapped: model.outputWrap }"
        :style="style(bounds.output)"
      >
        <FrameView
          class="script-editor-output-header"
          :scene="output"
          @event="emit('event', $event)"
        /><slot name="output" />
      </section>
      <AppSplitter
        v-if="!model.outputHidden"
        :style="style(bounds.outputSplitter)"
        horizontal
        :model-value="bounds.output.height"
        label="Output height"
        :min="80"
        :max="500"
        @update:model-value="
          emit('event', { type: 'outputHeight', value: $event })
        "
      />
      <div class="script-editor-code" :style="style(bounds.source)">
        <slot name="source" />
      </div>
      <div :style="style(bounds.footer)">
        <FrameView :scene="footer" @event="emit('event', $event)" />
      </div>
      <div class="script-editor-notice" :style="style(bounds.notice)">
        <slot name="notice" />
      </div>
    </div>
    <AppSplitter
      v-if="bounds.treeVisible"
      :style="style(bounds.treeSplitter)"
      reverse
      :model-value="bounds.tree.width"
      label="Scripts panel width"
      :min="160"
      :max="500"
      @update:model-value="emit('event', { type: 'treeWidth', value: $event })"
    />
    <aside
      v-if="bounds.treeVisible"
      class="script-editor-tree"
      :style="style(bounds.tree)"
    >
      <FrameView
        class="script-editor-side-tabs"
        :scene="side"
        @event="emit('event', $event)"
      />
      <div class="script-editor-side-content"><slot name="tree" /></div>
    </aside>
  </div>
</template>
<style>
.script-editor-workspace {
  flex: 1;
  min-width: 0;
  min-height: 0;
  position: relative;
}
.script-editor-workspace .script-editor-toolbar {
  overflow: auto;
}
.script-editor-workspace .script-editor-output {
  padding: 0;
  min-height: 0;
  border: 0;
  box-shadow: inset 0 0 0 1px var(--outline-variant);
}
.script-editor-output-header {
  height: 40px;
  flex-shrink: 0;
}
.script-editor-workspace .script-editor-tree {
  padding: 0;
  min-width: 0;
  border: 0;
  box-shadow: inset 0 0 0 1px var(--outline-variant);
}
.script-editor-side-tabs {
  height: 36px;
  flex-shrink: 0;
}
.script-editor-side-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 4px 4px;
}
.script-editor-notice {
  overflow: auto;
}
.script-editor-notice p {
  margin: 0;
}
</style>
