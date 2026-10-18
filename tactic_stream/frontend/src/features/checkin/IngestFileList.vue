<script setup>
import { computed } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import VirtualCollection from '../../controls/lists/VirtualCollection.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/ingest.ui.mjs';

const props = defineProps({ records: Array, busy: Boolean, frameNode: Object });
const emit = defineEmits(['remove']);
const items = computed(() =>
  props.records.map((record, index) => ({
    key: record.key,
    height: UI.fileHeight(record),
    data: { record, index }
  }))
);
</script>
<template>
  <div class="ingest-file-viewport">
    <VirtualCollection :items="items" :row-gap="4">
      <template #default="{ item }">
        <FrameView
          :style="{ height: UI.fileHeight(item.record) + 'px' }"
          :scene="
            UI.fileRow(
              { busy },
              item.record,
              item.index,
              Math.max(0, frameNode.width - 28),
              appearance.language
            )
          "
          @event="emit('remove', $event.index)"
        />
      </template>
    </VirtualCollection>
  </div>
</template>
<style>
.ingest-file-viewport {
  overflow: auto;
  scrollbar-gutter: stable;
  padding: 6px;
  box-sizing: border-box;
}
.ingest-file-viewport > .virtual-collection {
  width: calc(100% - 4px);
}
</style>
