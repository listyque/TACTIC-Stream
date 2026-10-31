<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import AppSearchField from '../../controls/AppSearchField.vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import * as Filters from '../../../../src/tactic_stream/shared_ui/features/table/page.filters.mjs';
const props = defineProps({
  model: Object,
  values: Object,
  ticket: String,
  project: String,
  disabled: Boolean
});
const emit = defineEmits(['apply']);
const text = ref(''),
  records = ref([]),
  error = ref(''),
  input = ref(null);
let timer,
  generation = 0;
const query = computed(() => {
  try {
    return Filters.query(props.model.layoutFilters, text.value);
  } catch {
    return { text: text.value };
  }
});
const suggestions = computed(() => {
  try {
    return Filters.suggestions(
      props.model.layoutFilters,
      text.value,
      records.value,
      appearance.language
    );
  } catch {
    return [];
  }
});
function clear() {
  clearTimeout(timer);
  ++generation;
  records.value = [];
  error.value = '';
}
function edit(value) {
  clear();
  text.value = value;
  if (value.trim()) timer = setTimeout(suggest, 180);
}
async function suggest() {
  const request = generation;
  try {
    const filter_query = Filters.query(props.model.layoutFilters, text.value);
    const result = await rpc(
      'execute_cmd',
      [
        { ticket: props.ticket, project: props.project },
        'tactic.ui.table.CustomLayoutReadCmd',
        {
          view: props.model.layoutView,
          search_key: props.model.targetSearchKey,
          filter_values: props.values,
          filter_query
        }
      ],
      {},
      true,
      true
    );
    if (request === generation) records.value = result.info.filterSuggestions;
  } catch (failure) {
    if (request === generation) error.value = failure.message;
  }
}
function apply(result) {
  text.value = result.text;
  clear();
  if (result.apply)
    emit('apply', Filters.values(props.model.layoutFilters, result.draft));
  else {
    input.value.focus();
    timer = setTimeout(suggest, 0);
  }
}
function accept(record) {
  try {
    apply(Filters.choose(props.model.layoutFilters, props.values, record));
  } catch (failure) {
    error.value = failure.message;
  }
}
function submit() {
  try {
    apply(
      Filters.submit(
        props.model.layoutFilters,
        props.values,
        text.value,
        suggestions.value
      )
    );
  } catch (failure) {
    error.value = failure.message;
  }
}
watch(
  () => [
    props.ticket,
    props.project,
    props.model.layoutView,
    props.model.targetSearchKey
  ],
  () => {
    clear();
    text.value = '';
  }
);
onBeforeUnmount(clear);
watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) clear();
  }
);
</script>
<template>
  <AppSearchField
    ref="input"
    :model-value="text"
    :placeholder="t('Search this page…')"
    label="Search this page…"
    :disabled="disabled"
    :suggestions="suggestions"
    :highlight-query="query.text"
    :error="error"
    :open-in-new-tab="false"
    @update:model-value="edit"
    @accept="accept"
    @search="submit"
    @dismiss="clear"
  />
</template>
