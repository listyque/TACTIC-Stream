<script setup>
import { computed, ref, onMounted, onBeforeUnmount, h } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppSearchField from '../../controls/AppSearchField.vue';
import WorkspaceSearch from '../workspace/WorkspaceSearch.vue';
import ObjectLinkList from './ObjectLinkList.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/links.ui.mjs';
const props = defineProps({
  model: Object,
  ticket: String,
  project: String,
  searchType: String,
  available: Array,
  linked: Array,
  availableSelected: Array,
  linkedSelected: Array,
  availableQuery: String,
  linkedQuery: String,
  hasMore: Boolean,
  total: Number
});
const emit = defineEmits(['event', 'query', 'select', 'drop', 'more']);
const host = ref(null),
  size = ref({ width: 0, height: 0 });
let observer;
const scene = computed(() =>
  UI.describe(
    props.model,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
const views = {};
for (const scope of ['available', 'linked']) {
  views[scope + 'Search'] = {
    component: (_, context) =>
      h(scope === 'available' ? WorkspaceSearch : AppSearchField, {
        ticket: props.ticket,
        project: props.project,
        searchType: props.searchType,
        suggestions:
          scope === 'linked' && props.linkedQuery.trim()
            ? props.linked
                .filter((row) =>
                  row.title
                    .toLocaleLowerCase()
                    .includes(props.linkedQuery.toLocaleLowerCase())
                )
                .slice(0, 20)
                .map((row) => ({ title: row.title, description: row.subtitle }))
            : [],
        onAccept: (row) => emit('query', scope, row.title, true),
        ...context.attrs,
        modelValue: props[scope + 'Query'],
        label:
          scope === 'available'
            ? 'Search available objects'
            : 'Search linked objects',
        placeholder: t(
          scope === 'available'
            ? 'Search available objects'
            : 'Search linked objects'
        ),
        disabled: props.model.saving || props.model.uncertain,
        'onUpdate:modelValue': (value) => emit('query', scope, value, false),
        onSearch: () => emit('query', scope, props[scope + 'Query'], true)
      })
  };
  views[scope + 'List'] = {
    component: (_, context) =>
      h(ObjectLinkList, {
        ...context.attrs,
        scope,
        records: props[scope],
        selected: props[scope + 'Selected'],
        total: scope === 'available' ? props.total : props.linked.length,
        busy: props.model.busy,
        disabled: props.model.saving || props.model.uncertain,
        hasMore: scope === 'available' && props.hasMore,
        onSelect: (key, modifiers) => emit('select', scope, key, modifiers),
        onDrop: (keys) => emit('drop', scope, keys),
        onMore: () => emit('more')
      })
  };
}
onMounted(() => {
  const measure = () => {
    size.value = {
      width: host.value.clientWidth,
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
  <section ref="host" class="object-link-surface">
    <FrameView :scene="scene" :views="views" @event="emit('event', $event)" />
  </section>
</template>
<style>
.object-link-surface {
  position: relative;
  min-width: 0;
  min-height: 0;
  flex: 1;
  height: 100%;
}
</style>
