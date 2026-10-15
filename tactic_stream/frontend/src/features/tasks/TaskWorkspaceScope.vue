<script setup>
// TasksWorkspaceView.qml scopeMenuActions: direct choices in the popup or narrow overflow.
import AppSelect from '../../controls/AppSelect.vue'
import AppMenuItem from '../../controls/AppMenuItem.vue'
import { t } from '../../i18n.js'
defineProps({ scope: String, identity: String, options: Array, catalog: Object, blocked: Boolean })
defineEmits(['scope', 'identity'])
</script>
<template>
  <div class="task-scope-fields" role="group" :aria-label="t('Task scope')">
    <AppMenuItem v-for="option in options" :key="option.value" :label="option.label" :icon="option.icon" :checked="option.value === scope" :disabled="blocked || option.disabled" @click="$emit('scope', option.value)" />
    <label v-if="scope === 'user' || scope === 'team'">{{ t(scope === 'team' ? 'Team' : 'User') }}<AppSelect :model-value="identity" :label="scope === 'team' ? 'Team' : 'User'" :translate-labels="false" :options="(scope === 'team' ? catalog?.teams : catalog?.users) || []" :disabled="blocked" @update:model-value="$emit('identity', $event)" /></label>
  </div>
</template>
