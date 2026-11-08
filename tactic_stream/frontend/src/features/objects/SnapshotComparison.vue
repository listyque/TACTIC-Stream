<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import AppSelect from '../../controls/AppSelect.vue';
import AppSlider from '../../controls/AppSlider.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/snapshot.ui.mjs';

const props = defineProps({ choices: Array, imageMode: String });
const emit = defineEmits(['close']);
const host = ref(null),
  size = ref({ width: 0, height: 0 });
const mode = ref('side'),
  position = ref(50),
  left = ref(''),
  right = ref('');
const pair = computed(() =>
  UI.comparisonPair(props.choices, left.value, right.value)
);
const a = computed({
  get: () => pair.value[0]?.value,
  set: (value) => (left.value = value)
});
const b = computed({
  get: () => pair.value[1]?.value,
  set: (value) => (right.value = value)
});
const alternatives = computed(() =>
  props.choices.filter((row) => row.snapshotId !== pair.value[0]?.snapshotId)
);
const layout = computed(() =>
  UI.comparisonLayout(
    size.value.width,
    size.value.height,
    mode.value,
    position.value
  )
);
const toolbar = computed(() =>
  UI.comparisonToolbar(mode.value, size.value.width, appearance.language)
);
const style = (bounds) => ({
  left: `${bounds.x}px`,
  top: `${bounds.y}px`,
  width: `${bounds.width}px`,
  height: `${bounds.height}px`
});
const source = (row) => row?.qualityUrl || row?.url || '';
let observer;
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    size.value = entry.contentRect;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <section
    ref="host"
    class="snapshot-comparison"
    :aria-label="t('Compare snapshots')"
    @keydown.esc.stop="emit('close')"
  >
    <FrameView
      :scene="toolbar"
      @event="$event.type === 'close' ? emit('close') : (mode = $event.value)"
    />
    <AppSelect
      v-model="a"
      class="snapshot-compare-port"
      :style="style(layout.pickers[0])"
      :options="choices"
      label="Snapshot A"
      display-prefix="A · "
      :translate-labels="false"
    />
    <AppSelect
      v-model="b"
      class="snapshot-compare-port"
      :style="style(layout.pickers[1])"
      :options="alternatives"
      label="Snapshot B"
      display-prefix="B · "
      :translate-labels="false"
    />
    <div
      class="snapshot-compare-port snapshot-compare-image"
      :style="style(layout.a)"
      data-comparison="A"
    >
      <ItemPreview
        :source="source(pair[0])"
        :aria-label="pair[0]?.label"
        :fill-mode="imageMode === 'fill' ? 'cover' : 'contain'"
        fallback-icon="image"
        :preview-size="58"
      />
    </div>
    <div
      class="snapshot-compare-port snapshot-compare-image"
      :style="style(layout.b)"
      data-comparison="B"
    >
      <div
        class="snapshot-compare-port"
        :style="
          style({
            x: layout.bOffset,
            y: 0,
            width: layout.bWidth,
            height: layout.b.height
          })
        "
      >
        <ItemPreview
          :source="source(pair[1])"
          :aria-label="pair[1]?.label"
          :fill-mode="imageMode === 'fill' ? 'cover' : 'contain'"
          fallback-icon="image"
          :preview-size="58"
        />
      </div>
    </div>
    <template v-if="mode === 'divider'">
      <div
        class="snapshot-compare-port snapshot-compare-line"
        :style="style(layout.line)"
        aria-hidden="true"
      />
      <AppSlider
        v-model="position"
        class="snapshot-compare-port"
        :style="style(layout.slider)"
        label="Image divider"
      />
    </template>
  </section>
</template>

<style>
.snapshot-comparison {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.snapshot-compare-port {
  position: absolute;
}
.snapshot-compare-image {
  overflow: hidden;
}
.snapshot-compare-image .image-picker-preview.item-preview {
  width: 100%;
  height: 100%;
  background: transparent;
}
.snapshot-compare-line {
  background: var(--outline);
  pointer-events: none;
}
</style>
