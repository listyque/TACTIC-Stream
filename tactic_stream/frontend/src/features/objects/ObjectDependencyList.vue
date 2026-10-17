<script setup>
import { computed } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import VirtualCollection from '../../controls/lists/VirtualCollection.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/delete.ui.mjs';

const props = defineProps({ models: Object, frameNode: Object });
const items = computed(() => (props.models[props.frameNode.source] || []).map(row => ({
  key: row.searchKey, data: row, height: UI.dependencyHeight(row)
})));
</script>

<template>
  <div class="object-dependencies-list">
    <VirtualCollection :items="items">
      <template #default="{item}">
        <FrameView :scene="UI.dependency(item, frameNode.width)"
          :style="{height: UI.dependencyHeight(item) + 'px'}" />
      </template>
    </VirtualCollection>
  </div>
</template>

<style>
.object-dependencies-list { overflow: auto; scrollbar-gutter: auto; }
</style>
