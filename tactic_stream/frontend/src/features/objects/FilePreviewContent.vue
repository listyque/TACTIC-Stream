<script>
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppIcon from '../../controls/AppIcon.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import { prettySize } from '../checkin/files.js'
import { downloadBlob } from '../../controls/files.js'
import { mobile } from '../../mobile.js'

export default {
  components: { AppButton, AppMenu, AppIcon, ItemPreview },
  props: { record: Object, cell: Object, embedded: Boolean, actionsTarget:Object, description:String },
  emits: ['session-expired', 'selected', 'busy'],
  data() { return { loading: false, error: '', mediaUrl: '', mediaType: '', text: '', selectedFile: null, request: 0 } },
  computed: { mobile() { return mobile.value } },
  watch: { loading(value) { this.$emit('busy', value) }, cell: { immediate:true, handler(cell) { this.reset(); if (cell?.loadFile && cell.files?.length) this.selectFile(cell.files.find(file => file.code === cell.fileCode) || cell.files.find(file => !['web', 'icon'].includes(file.type)) || cell.files[0]) } } },
  methods: {
    t,
    fileDetails(file) { return [file.filename?.includes('.') ? file.filename.split('.').at(-1).toUpperCase() : '', file.size != null ? prettySize(Number(file.size)) : '', file.type].filter(Boolean).join(' · ') },
    reset() { this.request++; if (this.mediaUrl) URL.revokeObjectURL(this.mediaUrl); this.mediaUrl = this.mediaType = this.text = this.error = ''; this.loading = false; this.selectedFile = null },
    async selectFile(file) {
      this.reset(); this.selectedFile = file; this.$emit('selected', file); this.loading = true
      const id = this.request
      try {
        const blob = await this.cell.loadFile(file)
        if (id !== this.request) return
        this.mediaUrl = URL.createObjectURL(blob); this.mediaType = blob.type
        if (blob.type.startsWith('text/')) { const text = await blob.slice(0, 100000).text(); if (id === this.request) this.text = text }
      } catch (error) { if (id === this.request) { this.error = error.message; if (error.code === 'authentication_failed') this.$emit('session-expired') } }
      finally { if (id === this.request) this.loading = false }
    },
    async download(file) {
      const id = this.request
      try {
        const blob = await this.cell.loadFile(file)
        if (id !== this.request) return
        downloadBlob(blob, file.filename)
      } catch (error) { if (id === this.request) { this.error = error.message; if (error.code === 'authentication_failed') this.$emit('session-expired') } }
    },
  },
  beforeUnmount() { this.reset() },
}
</script>
<template>
  <template v-if="cell">
      <AppMenu v-if="mobile && cell.loadFile && cell.files?.length > 1" class="file-preview-picker" label="Preview file" overlay show-label align-start :width="360">
        <template #trigger><ItemPreview fallback-icon="file" :preview-size="32" /><span class="file-preview-file-copy"><strong>{{ selectedFile?.filename }}</strong><small class="muted">{{ selectedFile && fileDetails(selectedFile) }}</small></span><AppIcon name="MDI_CHEVRON_DOWN" /></template>
        <AppButton v-for="(file,index) in cell.files" :key="file.code || index" class="file-preview-choice" role="menuitemradio" :aria-checked="file === selectedFile" :label="file.filename" :translate-label="false" @click="selectFile(file)">
          <ItemPreview fallback-icon="file" :preview-size="32" /><span class="file-preview-file-copy"><strong>{{ file.filename }}</strong><small class="muted">{{ fileDetails(file) }}</small></span><AppIcon v-if="file === selectedFile" name="check" />
        </AppButton>
      </AppMenu>
      <p v-if="error" class="error" role="alert">{{ t(error) }} <AppButton v-if="selectedFile" label="Retry" @click="selectFile(selectedFile)" /></p>
      <p v-if="loading" role="status">{{ t('Loading file…') }}</p>
      <div class="file-preview-content">
      <ItemPreview v-if="!cell.loadFile || mediaType.startsWith('image/') && mediaType !== 'image/svg+xml'" :source="mediaUrl || cell.image" fallback-icon="image" />
      <video v-else-if="mediaType.startsWith('video/')" :src="mediaUrl" controls preload="metadata"></video>
      <audio v-else-if="mediaType.startsWith('audio/')" :src="mediaUrl" controls preload="metadata"></audio>
      <iframe v-else-if="mediaType === 'application/pdf'" :src="mediaUrl" :title="selectedFile?.filename"></iframe>
      <pre v-else-if="mediaType.startsWith('text/')" class="file-preview-text">{{ text }}</pre>
      <p v-else-if="!loading" class="muted">{{ t('No preview available') }}</p>
      <p v-if="!cell.loadFile && !cell.image" class="muted">{{ t('No preview available') }}</p>
      <p v-if="description || record?.description" class="file-preview-description">{{ description || record.description }}</p>
      </div>
      <Teleport :to="actionsTarget || 'body'" :disabled="!mobile || !actionsTarget">
      <nav class="file-preview-actions">
      <div v-if="(embedded || mobile) && selectedFile" class="configuration-actions file-preview-download"><AppButton v-if="selectedFile.href" :href="selectedFile.href" label="Download" icon="download" :download="selectedFile.filename" /><AppButton v-else label="Download" icon="download" @click="download(selectedFile)" /></div>
      <component :is="mobile ? 'AppMenu' : 'div'" class="file-preview-details" label="File details" :overlay="mobile">
      <small v-if="mobile">{{ record?.__search_key__ }}</small>
      <dl v-if="cell.object" class="file-preview-metadata"><dt>{{ t('Search Type') }}</dt><dd>{{ cell.object.search_type }}</dd>
        <template v-for="name in ['code', 'status', 'description']" :key="name"><dt>{{ t({ code: 'Code', status: 'Status', description: 'Description' }[name]) }}</dt><dd>{{ record?.[name] || '—' }}</dd></template></dl>
      <dl class="file-preview-metadata"><dt>{{ t('Context') }}</dt><dd>{{ cell.context || '—' }}</dd><dt>{{ t('Version') }}</dt><dd>{{ cell.version ?? '—' }}</dd></dl>
      <ul v-if="cell.files?.length" class="file-preview-files">
        <li v-for="(file, index) in cell.files" :key="index">
          <div><strong>{{ file.filename }}</strong><small class="muted">{{ file.type }} · {{ file.size ?? '—' }} {{ t('bytes') }}</small><small class="muted">{{ file.path }}</small></div>
          <div v-if="file.href" class="configuration-actions"><AppButton :href="file.href" label="Open file" icon="link" target="_blank" rel="noopener noreferrer" /><AppButton :href="file.href" label="Download" icon="download" :download="file.filename" /></div>
          <div v-else-if="cell.loadFile" class="configuration-actions"><AppButton label="Open file" icon="link" :disabled="loading" @click="selectFile(file)" /><AppButton label="Download" icon="download" @click="download(file)" /></div>
        </li>
      </ul>
      <p v-else class="muted">{{ t('No files') }}</p>
      </component>
      </nav>
      </Teleport>

  </template>
</template>
<style>
.file-preview-actions { display:contents; }
.file-preview-description { margin:8px 0; font-size:var(--text-body); white-space:pre-wrap; overflow-wrap:anywhere; }
@media(max-width:700px) {
  .file-preview-actions { display:flex; flex:none; justify-content:space-between; align-items:center; gap:8px; padding:4px 8px max(4px,env(safe-area-inset-bottom)); background:var(--surface-high); }
  .file-preview-actions .file-preview-download { margin:0; }
  .file-preview-actions .file-preview-download .app-button { min-height:32px; font-size:var(--text-label); padding:4px 10px; }
  .file-preview-actions > .file-preview-details { margin:0; align-self:center; }
  .file-preview-actions > .file-preview-details > summary { width:32px; height:32px; }
}
.file-preview-picker { flex-shrink:0; min-width:0; }
.file-preview-picker.labelled-menu > summary { display:flex; width:100%; height:48px; padding:4px 8px; gap:8px; border-radius:var(--item-radius); background:var(--surface-high); box-sizing:border-box; }
.file-preview-picker .account-panel { overflow-x:hidden; }
.file-preview-picker .account-panel > .file-preview-choice { width:100%; height:52px; gap:8px; padding:4px 8px; }
.file-preview-picker .file-preview-choice[aria-checked="true"] { background:var(--content-selection); }
.file-preview-picker .image-picker-preview { flex:none; width:32px; height:32px; border-radius:var(--item-radius); background:var(--primary); color:var(--on-selected); }
.file-preview-file-copy { display:flex; flex:1; min-width:0; flex-direction:column; gap:2px; text-align:left; }
.file-preview-file-copy > strong,.file-preview-file-copy > small { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.file-preview-file-copy > strong { font-size:var(--text-body); font-weight:500; }
.file-preview-file-copy > small { font-size:var(--text-caption); }
.file-preview-picker :is(summary,.file-preview-choice) > .app-icon { flex:none; width:16px; height:16px; font-size:16px; }
</style>
