<script setup>
import { ref, nextTick } from 'vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import ResultItem from '../../frontend/src/features/workspace/ResultItem.vue';
import ConditionCards from '../../frontend/src/features/workspace/ConditionCards.vue';
import SearchPresetBar from '../../frontend/src/features/workspace/SearchPresetBar.vue';
import SearchEditorPart from '../../frontend/src/features/workspace/SearchEditorPart.vue';
import SearchFooter from '../../frontend/src/features/workspace/SearchFooter.vue';
import VirtualCollection from '../../frontend/src/controls/lists/VirtualCollection.vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import * as Popups from '../../src/tactic_stream/shared_ui/features/search/popups.ui.mjs';
import * as Visibility from '../../src/tactic_stream/shared_ui/features/search/visibility.ui.mjs';

const fixture = ref(null),
  items = ref([]),
  events = ref([]),
  scroll = ref(null);
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
Object.assign(appearance, {
  clickAnimations: false,
  hoverAnimations: false,
  fadeAnimations: false,
  popupAnimations: false
});
initializeAppearance();
window.searchFixture = {
  async show(value) {
    Object.assign(appearance, {
      theme: value.style,
      mode: value.dark ? 'dark' : 'light',
      language: value.language
    });
    fixture.value = value;
    items.value = [];
    events.value = [];
    await nextTick();
    await document.fonts.ready;
  },
  async collection(count, tile = false) {
    fixture.value = {
      screen: 'collection',
      width: 800,
      height: 600,
      language: 'en',
      dark: true,
      style: 'md3',
      tile
    };
    items.value = Array.from({ length: count }, (_, index) => ({
      key: String(index),
      data: {
        id: String(index),
        kind: 'object',
        title: 'Asset ' + index,
        record: { name: 'Asset ' + index },
        hasChildren: false
      },
      height: tile ? 244 : index % 3 ? 100 : 64
    }));
    await nextTick();
    scroll.value.scrollTop = 0;
  },
  events: () => [...events.value]
};
function send(action) {
  events.value.push(action);
}
</script>
<template>
  <main
    v-if="fixture"
    id="search-fixture"
    :style="{
      width: fixture.width + 'px',
      height: fixture.height + 'px',
      background: 'var(--surface)'
    }"
  >
    <div v-if="fixture.screen === 'advanced'" class="search-fixture-advanced">
      <SearchPresetBar
        :model="{
          presets: fixture.presets,
          selected: '',
          canManage: true,
          busy: fixture.busy
        }"
        @event="send"
      />
      <ConditionCards
        :model="{
          rows: fixture.rows,
          columns: fixture.columns,
          busy: fixture.busy,
          reorder: true
        }"
        @event="send"
      />
      <SearchEditorPart
        part="tabName"
        :model="{ title: 'Assets', busy: fixture.busy }"
        @event="send"
      />
    </div>
    <ResultItem
      v-else-if="fixture.node"
      :node="fixture.node"
      :card="fixture.screen.startsWith('card')"
      :compact="fixture.compact"
      :tree="!fixture.screen.startsWith('card')"
      :selected="fixture.selected"
      @activate="send"
    />
    <SearchFooter
      v-else-if="fixture.screen === 'footer'"
      :model="fixture.model"
      @event="send"
    />
    <FrameView
      v-else-if="fixture.screen === 'tags'"
      :scene="Popups.tagHeader(fixture.model, fixture.width, fixture.language)"
      @event="send"
    />
    <FrameView
      v-else-if="fixture.screen === 'quick'"
      :scene="
        Popups.quickHeader(fixture.model, fixture.width, fixture.language)
      "
      @event="send"
    />
    <FrameView
      v-else-if="fixture.screen === 'visibility'"
      :scene="Visibility.footer(fixture.model, fixture.width, fixture.language)"
      @event="send"
    />
    <div
      v-else-if="fixture.screen === 'collection'"
      ref="scroll"
      class="search-fixture-scroll"
    >
      <VirtualCollection
        :items="items"
        :cell-width="fixture.tile ? 212 : undefined"
        :column-gap="fixture.tile ? 18 : 0"
        :row-gap="fixture.tile ? 14 : 3"
      >
        <template #default="{ item: node }"
          ><ResultItem
            :node="node"
            :tree="!fixture.tile"
            :card="fixture.tile"
            :compact="Number(node.id) % 3 === 0"
            @activate="send"
        /></template>
      </VirtualCollection>
    </div>
  </main>
</template>
<style>
html,
body,
#app {
  margin: 0;
  min-width: 0;
}
#search-fixture {
  position: relative;
  overflow: hidden;
  color: var(--on-surface);
}
.search-fixture-advanced {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  overflow: auto;
  height: 100%;
  scrollbar-gutter: stable;
}
.search-fixture-advanced > * {
  flex: none;
}
.search-fixture-advanced .search-library-conditions {
  overflow: visible;
  flex: none;
}
.search-fixture-scroll {
  height: 100%;
  overflow: auto;
}
</style>
