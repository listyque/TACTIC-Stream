<script setup>
import { debugSettings, levels } from './debugLog.js'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import SettingRow from '../../controls/SettingRow.vue'
import { t } from '../../i18n.js'
const props = defineProps({ settings:{ type:Object, default:() => debugSettings } })
function toggle(level, checked) { props.settings.recordingLevels = checked ? levels.filter(item => item === level || props.settings.recordingLevels.includes(item)) : props.settings.recordingLevels.filter(item => item !== level) }
</script>
<template>
  <section class="content debug-recording-settings"><h2>{{ t('Debug Log') }}</h2><p class="muted">{{ t('Choose which events are recorded. Level filters in Debug Log only hide recorded events. Errors and critical events are recorded by default.') }}</p>
    <div class="configuration-group"><SettingRow v-for="level in levels" :key="level" :control-id="'record-debug-' + level" :title="level" :description="{ LOG: 'General application messages.', INFO: 'Informational application events.', WARNING: 'Recoverable issues and warnings.', MISSING: 'Missing files and resources.', EXCEPTION: 'Unhandled exceptions.', ERROR: 'Failed requests and application errors.', CRITICAL: 'Critical application failures.', API: 'Successful API calls, including arguments, results and duration.' }[level]">
      <AppCheckbox :control-id="'record-debug-' + level" :model-value="settings.recordingLevels.includes(level)" :label="t('Record {level}', { level })" @update:model-value="toggle(level, $event)" />
    </SettingRow></div>
    <p class="muted">{{ t('Debug sessions are stored in this browser. Download a session to share it. Signing out clears local sessions. Tickets and credentials are redacted.') }}</p>
  </section>
</template>
