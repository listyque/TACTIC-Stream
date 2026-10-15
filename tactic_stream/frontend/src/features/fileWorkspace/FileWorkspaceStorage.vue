<script setup>
import { t } from '../../i18n.js'
import { prettySize } from '../checkin/files.js'
import AppButton from '../../controls/AppButton.vue'
import AppTextField from '../../controls/AppTextField.vue'
defineProps({ status:Object, draft:Object, busy:Boolean, indexing:Boolean, filesService:Boolean })
const emit=defineEmits(['change','save','reset','action','stop'])
const fields=[['bytes_limit','Byte quota','Zero means unlimited.'],['files_limit','File quota','Zero means unlimited.'],['max_parallel','Parallel transfers','From 1 to 16.'],['upload_retention_seconds','Unfinished uploads (seconds)','Zero disables expiration.'],['reverted_retention_seconds','Reverted changelists (seconds)','Zero disables expiration.'],['task_retention_seconds','Completed tasks (seconds)','Zero disables expiration.'],['shelf_retention_seconds','Shelved changelists (seconds)','Zero disables expiration.'],['gc_grace_seconds','Quarantine before deletion (seconds)','Unreferenced contents stay in quarantine before physical deletion.'],['gc_interval_seconds','Automatic GC interval (seconds)','Zero disables automatic cleanup.']]
</script>
<template>
  <section class="storage-administration" :aria-label="t('Storage administration')">
    <div class="storage-fields">
      <h3>{{ t('Storage administration') }}</h3>
      <p>{{ prettySize(status?.allocated_bytes||0) }} · {{ status?.allocated_files||0 }} {{ t('files') }} · {{ t(status?.indexed?'Storage index complete':'Storage index incomplete') }}</p>
      <div class="storage-actions"><AppButton label="Refresh" icon="refresh" :disabled="busy" @click="emit('action','storage_status')" /><AppButton v-if="!status?.initialized" label="Initialize storage" :disabled="busy" @click="emit('action','storage_upgrade')" /><AppButton v-else-if="!status.indexed" label="Continue storage index" :disabled="busy" @click="emit('action','storage_index')" /><AppButton v-if="indexing" label="Stop waiting" icon="close" @click="emit('stop')" /></div>
      <p v-if="!status?.indexed">{{ t('Finish indexing before editing the policy or running GC. Indexing can be stopped and continued.') }} <span v-if="status?.index_table!==undefined">{{ t('Table') }}: {{ status.index_table }} · {{ status.index_after }}</span></p>
      <form v-if="draft" @submit.prevent="emit('save')">
        <template v-for="([key,label,hint],index) in fields" :key="key"><h3 v-if="index===0||index===3">{{ t(index===0?'Quotas':'Retention and cleanup') }}</h3><label><span>{{ t(label) }}</span><AppTextField :model-value="draft.policy[key]" :label="label" inputmode="numeric" :disabled="busy||!status?.indexed" @update:model-value="emit('change',{...draft,policy:{...draft.policy,[key]:$event}})" /><small>{{ t(hint) }}</small></label></template>
        <div class="storage-actions"><AppButton label="Reset" icon="undo" :disabled="busy" @click="emit('reset')" /><AppButton label="Save storage policy" icon="save" type="submit" :disabled="busy||!status?.indexed" /></div>
      </form>
      <h3>{{ t('Garbage collection') }}</h3><p>{{ t('Dry run counts unused objects without deleting them. Safe GC expires retained records and quarantines unused contents according to the saved policy.') }}</p>
      <p v-if="!filesService">{{ t('Enable the files service on the server to process GC tasks.') }}</p>
      <div class="storage-actions"><AppButton label="GC dry run" :disabled="busy||!status?.indexed||!filesService||['queued','running'].includes(status?.gc?.state)" @click="emit('action','gc_begin',true)" /><AppButton label="Run safe GC" :disabled="busy||!status?.indexed||!filesService||['queued','running'].includes(status?.gc?.state)" @click="emit('action','gc_begin',false)" /><AppButton v-if="['queued','running'].includes(status?.gc?.state)" label="Cancel GC" icon="close" :disabled="busy" @click="emit('action','gc_cancel')" /></div>
      <div v-if="status?.gc" class="gc-status" role="status"><p>{{ status.gc.code }} · {{ t(status.gc.state) }} · {{ status.gc.phase }} · {{ t(status.gc.dry_run?'GC dry run':'Run safe GC') }}</p><p>{{ t('Objects scanned') }}: {{ status.gc.objects_done }} · {{ t('Candidates') }}: {{ status.gc.candidates }} · {{ prettySize(status.gc.candidate_bytes||0) }}</p><p>{{ t('Expired records') }}: {{ status.gc.expired }} · {{ t('Quarantined') }}: {{ status.gc.quarantined }} · {{ t('Purged') }}: {{ status.gc.purged }}</p><p v-if="status.gc.error" role="alert">{{ status.gc.error }}</p><p v-if="status.gc.state==='error'">{{ t('GC stopped. After fixing the cause, start a new dry run or safe GC.') }}</p></div>
    </div>
  </section>
</template>
<style scoped>
.storage-administration{flex:1;min-height:0;overflow:auto;padding:7px;border:1px solid var(--outline-variant);border-radius:var(--surface-radius);background:var(--surface-deep)}.storage-fields{max-width:660px;display:flex;flex-direction:column;gap:8px}.storage-fields form,.storage-fields label{display:flex;flex-direction:column;gap:8px}.storage-fields h3,.storage-fields p{margin:0}.storage-fields h3{font-size:var(--text-title);line-height:20px}.storage-fields p,.storage-fields small{color:var(--muted);overflow-wrap:anywhere}.storage-fields label>span{color:var(--muted)}.storage-fields p,.storage-fields label{line-height:17px}.storage-fields small{font-size:var(--text-caption);line-height:15px}.storage-actions{display:flex;flex-wrap:wrap;gap:8px}
</style>
