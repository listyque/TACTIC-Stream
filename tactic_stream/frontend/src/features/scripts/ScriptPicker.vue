<script setup>
import { computed, ref, watch } from 'vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppSearchField from '../../controls/AppSearchField.vue';
import NavigationTree from '../workspace/NavigationTree.vue';
import { scriptTree } from './scriptShelf.js';
import { t } from '../../i18n.js';

const props = defineProps({
  scripts: Array,
  modelValue: String,
  disabled: Boolean,
  scopeKey: String,
  anchor: Object
});
const emit = defineEmits(['update:modelValue']);
const menu = ref(null),
  query = ref('');
const openedScope = ref(null);
const entries = computed(() => scriptTree(props.scripts));
watch(
  () => props.scopeKey,
  () => {
    if (menu.value) menu.value.open = false;
  }
);
function select(row) {
  if (props.disabled || openedScope.value !== props.scopeKey) {
    if (menu.value) menu.value.open = false;
    return;
  }
  menu.value?.close(true);
  emit('update:modelValue', row.key);
}
function beforeOpen() {
  openedScope.value = props.scopeKey;
  query.value = '';
}
defineExpose({
  open() {
    if (!props.disabled && menu.value) menu.value.open = true;
  }
});
</script>
<template>
  <AppMenu
    ref="menu"
    class="script-picker"
    overlay
    external-trigger
    :anchor="anchor"
    :label="modelValue || 'Choose script'"
    :close-on-select="false"
    :disabled="disabled"
    @before-open="beforeOpen"
  >
    <strong>{{ t('Choose script') }}</strong>
    <AppSearchField
      v-model="query"
      label="Search scripts"
      :placeholder="t('Search scripts')"
    />
    <NavigationTree
      :entries="entries"
      :query="query"
      :selected="modelValue"
      @select="select"
    />
  </AppMenu>
</template>
