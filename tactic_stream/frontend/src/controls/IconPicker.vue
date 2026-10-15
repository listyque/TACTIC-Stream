<script setup>
import { computed, ref } from 'vue'
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'
import AppSelect from './AppSelect.vue'
import { t } from '../i18n.js'
import { appearance, iconSets } from '../appearance.js'
import { iconMaps } from '../icons.js'

const props = defineProps({ modelValue: String, disabled: Boolean, iconOnly: Boolean, tacticCompatibleOnly:Boolean })
const emit = defineEmits(['update:modelValue'])
const dialog = ref(null), search = ref(''), family = ref('material-design'), page = ref(0)
const names = computed(() => Object.keys(iconMaps[family.value]).sort().filter(name => name.includes(search.value.toLowerCase().trim())))
const value = name => props.tacticCompatibleOnly?name:family.value + ':' + name
function open() {
  const explicit = props.modelValue?.split(':')[0]
  const legacy = /^(FA|FAS|FAR|MDI)_/i.exec(props.modelValue || '')
  const preferred = iconMaps[explicit] ? explicit : legacy ? ({ FA: 'fontawesome-solid', FAS: 'fontawesome-solid', FAR: 'fontawesome-outline', MDI: 'material-design' })[legacy[1].toUpperCase()] : appearance.iconSet
  family.value = props.tacticCompatibleOnly?'fontawesome-solid':iconMaps[preferred] ? preferred : 'material-design'
  search.value = ''; page.value = 0; dialog.value.showModal()
}
function select(name) { emit('update:modelValue', value(name)); dialog.value.close() }
</script>

<template>
  <AppButton :icon="modelValue || 'link'" :icon-only="iconOnly" label="Choose icon" :disabled="disabled" @click="open" />
  <dialog ref="dialog" class="record-dialog icon-picker" :aria-label="t('Choose icon')">
    <header><h2>{{ t('Choose icon') }}</h2><AppButton label="Close" icon="close" @click="dialog.close()" /></header>
    <label v-if="!tacticCompatibleOnly">{{ t('Icon set') }}<AppSelect v-model="family" :options="iconSets.filter(option => iconMaps[option.value])" label="Icon set" @update:model-value="page = 0" /></label>
    <input v-model="search" type="search" :placeholder="t('Find an icon')" :aria-label="t('Find an icon')" @input="page = 0">
    <div class="icon-library"><AppButton v-for="name in names.slice(page * 80, (page + 1) * 80)" :key="name" :aria-label="name" :title="name" @click="select(name)"><AppIcon :name="family + ':' + name" /><small>{{ name }}</small></AppButton></div>
    <footer class="configuration-actions"><AppButton label="Previous" icon="previous" :disabled="page === 0" @click="page--" /><span>{{ page + 1 }} / {{ Math.max(1, Math.ceil(names.length / 80)) }}</span><AppButton label="Next" icon="next" :disabled="(page + 1) * 80 >= names.length" @click="page++" /></footer>
  </dialog>
</template>
