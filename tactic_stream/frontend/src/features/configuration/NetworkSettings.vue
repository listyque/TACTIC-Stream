<script setup>
import { t } from '../../i18n.js'
import SettingRow from '../../controls/SettingRow.vue'
import AppSelect from '../../controls/AppSelect.vue'
import { networkSettings, updateIntervals, updateModes, updateBatchDelays } from '../connection/networkSettings.js'
defineProps({ settings:{ type:Object, default:() => networkSettings } })
</script>

<template>
  <section class="content"><h2>{{ t('Background checks') }}</h2>
    <p class="muted">{{ t('Committed changes are coalesced by one server worker. Only subscribed data is refreshed; presence and authentication keep their own heartbeat.') }}</p>
    <div class="configuration-group"><SettingRow title="Update delivery" description="Choose periodic checks or a persistent server push connection. Commands and file uploads use the same API." control-id="server-update-mode">
      <AppSelect id="server-update-mode" v-model="settings.updateMode" label="Update delivery" :options="updateModes" />
    </SettingRow><SettingRow v-if="settings.updateMode === 'poll'" title="Server updates" description="Interval for the shared server request. Changing it also updates the Connection menu." control-id="server-update-interval">
      <AppSelect id="server-update-interval" v-model="settings.pollInterval" label="Server updates" :options="updateIntervals" />
    </SettingRow><SettingRow v-if="settings.updateMode === 'sse'" title="Update batching delay" description="Combine arriving changes before reading data. A longer delay reduces requests during bursts; it also delays visible updates." control-id="server-update-batch-delay">
      <AppSelect id="server-update-batch-delay" v-model="settings.batchDelay" label="Update batching delay" :options="updateBatchDelays" />
    </SettingRow></div>
  </section>
</template>
