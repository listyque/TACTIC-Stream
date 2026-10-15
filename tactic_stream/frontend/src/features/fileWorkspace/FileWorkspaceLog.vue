<script setup>
import { ref, watch, nextTick } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'

const props = defineProps({ entries:Array })
defineEmits(['clear','copy','debug'])
const expanded = ref(true), scroll = ref(null)
watch(() => props.entries.at(-1)?.id, async () => { await nextTick(); if(scroll.value)scroll.value.scrollTop=scroll.value.scrollHeight })
</script>
<template>
  <section class="file-operation-log" :aria-label="t('Operation log')">
    <header>
      <AppButton icon-only :label="expanded ? 'Collapse log' : 'Expand log'" :icon="expanded ? 'chevron-down' : 'next'" :aria-expanded="expanded" @click="expanded=!expanded" />
      <AppIcon name="MDI_CONSOLE" /><strong>{{ t('Log') }}</strong>
      <AppButton icon-only label="Copy log" icon="copy" @click="$emit('copy')" />
      <AppButton icon-only label="Clear log" icon="delete" @click="$emit('clear')" />
      <AppButton icon-only label="Debug Log" icon="MDI_BUG" @click="$emit('debug')" />
    </header>
    <div v-show="expanded" ref="scroll" class="file-operation-log-scroll" role="log" aria-live="polite" :aria-label="t('Operation log')">
      <div v-for="entry in entries" :key="entry.id" class="file-operation-log-entry" :data-level="entry.level">
        <AppIcon :name="entry.level==='ERROR' ? 'error' : entry.level==='WARNING' ? 'warning' : 'info'" />
        <span>{{ entry.time }} · {{ entry.operation }} · {{ entry.message }}<span v-if="entry.path" class="file-operation-log-path">{{ entry.path }}</span></span>
      </div>
    </div>
  </section>
</template>
<style scoped>
.file-operation-log{flex-shrink:0;min-width:0;border:1px solid var(--outline-variant);border-radius:var(--surface-radius);background:var(--surface-deep)}
header{display:flex;align-items:center;gap:6px;padding:2px 4px;min-height:28px}
strong{flex:1;font-size:var(--text-label);font-weight:500}
.file-operation-log-scroll{height:100px;max-height:20vh;overflow:auto;scrollbar-gutter:stable;padding:4px 8px;font-size:var(--text-caption)}
.file-operation-log-entry{display:flex;align-items:flex-start;gap:6px;padding:2px 0;white-space:pre-wrap;overflow-wrap:anywhere;user-select:text}
.file-operation-log-entry>span{min-width:0}
.file-operation-log-entry>.app-icon{flex-shrink:0}
.file-operation-log-entry[data-level="ERROR"]{color:var(--error)}
.file-operation-log-entry[data-level="WARNING"]>.app-icon{color:var(--yellow)}
.file-operation-log-path{display:block}
</style>
