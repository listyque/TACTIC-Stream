<script setup>
import { computed, ref } from 'vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppSearchField from '../../controls/AppSearchField.vue'
import NavigationTree from '../workspace/NavigationTree.vue'
import { scriptTree } from './scriptShelf.js'
import { t } from '../../i18n.js'

const props = defineProps({ scripts: Array, modelValue: String, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
const menu = ref(null), query = ref('')
const entries = computed(() => scriptTree(props.scripts))
function select(row) { emit('update:modelValue', row.key); menu.value.open = false }
</script>
<template>
  <AppMenu ref="menu" class="script-picker" overlay :label="modelValue || 'Choose script'" icon="MDI_FILE_TREE" :close-on-select="false" :inert="disabled" @toggle="query = ''">
    <template #trigger><AppIcon name="MDI_FILE_TREE" /><span>{{ modelValue || t('Choose script') }}</span><AppIcon name="MDI_CHEVRON_DOWN" /></template>
    <strong>{{ t('Choose script') }}</strong>
    <AppSearchField v-model="query" label="Search scripts" :placeholder="t('Search scripts')" />
    <NavigationTree :entries="entries" :query="query" :selected="modelValue" @select="select" />
  </AppMenu>
</template>
