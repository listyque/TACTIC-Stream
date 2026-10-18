<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { metrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/scope.ui.mjs';
import { t } from '../../i18n.js';
const props = defineProps({
  scope: String,
  identity: String,
  catalog: Object,
  blocked: Boolean,
  currentUser: String,
  searchTypeTitle: String,
  searchTypeAvailable: Boolean,
  selectedIcon: String
});
const emit = defineEmits(['scope']);
const host = ref(null),
  width = ref(0),
  chooseTeam = ref(false);
const scene = computed(() =>
  UI.describe(
    {
      scope: props.scope,
      identity: props.identity,
      personal: props.identity === props.currentUser,
      selectedIcon: props.selectedIcon,
      searchTypeTitle: props.searchTypeTitle,
      searchTypeAvailable: props.searchTypeAvailable,
      teams: props.catalog?.teams || [],
      users: props.catalog?.users || [],
      blocked: props.blocked,
      chooseTeam: chooseTeam.value,
      radius: metrics(appearance.theme).itemRadius
    },
    width.value,
    appearance.language
  )
);
function event(action) {
  if (action.type === 'scope' && action.value === 'team')
    chooseTeam.value = true;
  else if (action.type === 'scope') {
    chooseTeam.value = false;
    emit('scope', action.value);
  } else if (action.type === 'identity') {
    chooseTeam.value = false;
    emit('scope', action.scope, action.value);
  }
}
defineExpose({
  showTeams: () => {
    chooseTeam.value = true;
  },
  reset: () => {
    chooseTeam.value = false;
  }
});
let observer;
onMounted(() => {
  const measure = () => {
    width.value = frameContentWidth(host.value);
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="task-scope-fields"
    role="group"
    :aria-label="t('Task scope')"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" @event="event" />
  </div>
</template>
<style>
.task-scope-fields {
  position: relative;
  width: 100%;
  min-width: 0;
}
</style>
