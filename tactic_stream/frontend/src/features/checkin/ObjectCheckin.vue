<script>
import { nextTick, useId } from 'vue'
import { mobile } from '../../mobile.js'
import { resultItems, navigationLink, rpc, uploadFormFile } from '../../api.js'
import { t } from '../../i18n.js'
import { preferences } from '../configuration/preferences.js'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import SettingRow from '../../controls/SettingRow.vue'

export default {
  setup() { return { formId: useId() } },
  components: { AppButton, AppSelect, AppSwitch, SettingRow },
  inject: { queueCheckin: { default: null }, checkinDescription: { default:() => '' } },
  props: { ticket: String, project: String },
  data() { return { owner: null, scope: null, files: [], processes: [], process: 'publish', context: 'publish',
    description: '', mode: 'group', preview: false, clipboard: false, revision: false, version: null, confirmed: false,
    appendSnapshot:null, appendUncertain:false, existingFiles:[], keepFileName: false, repositories:[], repositoryAlias:'default', ready: false, busy: false, error: '', discard: false, request: 0 } },
  emits: ['attached'],
  watch: { ticket() { this.reset() }, project() { this.reset() } },
  computed: { mobile() { return mobile.value }, title() { return this.appendSnapshot ? 'Attach files' : this.preview ? 'Change Preview' : this.revision ? 'Add revision (override current file)' : this.clipboard ? 'Save from Clipboard' : 'Save snapshot' } },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.request++; window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    t,
    beforeUnload(event) { if (this.files.length) { event.preventDefault(); event.returnValue = '' } },
    reset() { this.request++; this.files = []; this.$refs.dialog?.close() },
    close(force = false) { force = force === true; if (this.busy && this.ready && !force) return; if (this.files.length && !force) { this.discard = true; return }; this.reset() },
    async open(record, options = {}) {
      const request = ++this.request
      this.scope = { ticket: this.ticket, project: this.project }
      this.owner = record; this.files = []; this.processes = []; this.error = ''; this.discard = false
      this.appendSnapshot = null; this.appendUncertain = false; this.existingFiles = []
      this.repositories = []; this.repositoryAlias = preferences.repository.defaultAlias
      this.description = this.checkinDescription(); this.mode = preferences.checkin.groupCheckin ? 'group' : 'individual'; this.keepFileName = preferences.checkin.keepFilename; this.confirmed = !preferences.checkin.confirmRevision
      if (options.checkinType === 'file') this.mode = 'individual'
      if (options.checkinType === 'multi_file') this.mode = 'group'
      this.preview = !!options.preview; this.clipboard = !!options.clipboard; this.revision = !!options.revision; this.version = null
      this.process = options.process || (this.preview ? 'icon' : 'publish'); this.context = options.context && options.context !== this.process ? options.context : ''
      this.busy = true; this.ready = false
      await nextTick(); this.$refs.dialog.showModal()
      try {
        if (['move','local','inplace'].includes(options.transferMode) || ['sequence','dir'].includes(options.checkinType)) throw new Error('This configured check-in mode requires a desktop connection.')
        if (record.__search_key__.startsWith('sthpw/snapshot?')) {
          const target = await navigationLink(this.scope.ticket, this.scope.project, 'skey://' + record.__search_key__)
          if (request !== this.request) return
          if (!target.parent) throw new Error('Object no longer exists')
          this.owner = target.parent; this.context = record.context; this.process = record.process || record.context.split('/')[0]
          if (options.append) {
            this.appendSnapshot = record.version < 0 ? await rpc('get_snapshot', [this.scope, this.owner.__search_key__], { context:record.context }) || record : record
            const snapshot = await navigationLink(this.scope.ticket, this.scope.project, 'skey://' + this.appendSnapshot.__search_key__)
            if (request !== this.request) return
            this.existingFiles = snapshot.preview?.files || []
          }
          if (this.revision && record.version >= 0) this.version = record.version
        }
        const type = this.owner.__search_key__.split('?')[0]
        const data = await resultItems(this.scope.ticket, this.scope.project, type, [this.owner.__search_key__])
        if (request !== this.request) return
        this.processes = data.items[0].branches.filter(branch => branch.kind === 'process').map(branch => ({ value: branch.process, label: branch.title }))
        if (this.preview) this.process = this.context = 'icon'
        if (!this.processes.some(item => item.value === this.process)) this.processes.unshift({ value: this.process, label: this.process })
        const configured = await rpc('get_base_dirs',[this.scope],{},true)
        if (request !== this.request) return
        const paths = value => typeof value === 'object' && value ? value : value?.startsWith('{') ? JSON.parse(value) : value ? { default:value } : {}
        const aliases = [...new Set(['default',...Object.keys(paths(configured.asset_base_dir)),...Object.keys(paths(configured.base_dir_alias))])]
        const labels = paths(configured.repository_display)
        this.repositories = aliases.filter(alias => alias !== 'plugins' && (preferences.repository.enabledAliases === null || preferences.repository.enabledAliases.includes(alias))).map(alias => ({ value:alias,label:labels[alias]?.title || alias }))
        if (!this.repositories.length) throw new Error('Enable at least one repository and choose its default.')
        if (!this.repositories.some(item => item.value === this.repositoryAlias)) this.repositoryAlias = this.repositories[0].value
        this.ready = true
        if (options.clipboard) await this.readImage()
      } catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
    addFiles(files) {
      const incoming = [...files]
      if (incoming.some(file => this.preview && !file.type.startsWith('image/'))) { this.error = 'Choose an image for the preview'; return }
      this.files.push(...incoming); this.error = ''
    },
    paste(event) { if (event.clipboardData?.files.length) { event.preventDefault(); this.addFiles(event.clipboardData.files) } },
    async readImage() {
      if (!navigator.clipboard?.read) { this.error = 'Paste an image with Ctrl+V or choose a file on HTTP.'; return }
      const request = this.request
      try {
        const files = []
        for (const item of await navigator.clipboard.read()) {
          const type = item.types.find(type => type.startsWith('image/'))
          if (type) files.push(new File([await item.getType(type)], 'clipboard-' + (files.length + 1) + '.' + type.split('/')[1], { type }))
        }
        if (request !== this.request) return
        if (!files.length) throw new Error('No image in clipboard')
        this.addFiles(files)
      } catch (error) { if (request === this.request) this.error = error.message }
    },
    submit() {
      if (this.appendSnapshot) return this.attachFiles()
      if (!this.ready || this.busy || !this.files.length || !(this.context.trim() || this.process) || this.revision && !this.confirmed) return
      if (new Set(this.files.map(file => file.name)).size !== this.files.length) { this.error = 'Choose different file names for a group check-in'; return }
      try {
        const values = { ...this.scope, searchKey: this.owner.__search_key__, title: this.owner.name || this.owner.title || this.owner.code,
          process: this.process, context: this.context.trim() || this.process, description: this.description, isRevision: this.revision, version: this.version, keepFileName: this.keepFileName, generatePreviews:preferences.checkin.generatePreviews, ...(this.revision ? {} : { repositoryAlias:this.repositoryAlias }) }
        const groups = this.mode === 'individual' ? this.files.map(file => [file]) : [this.files]
        for (const files of groups) this.queueCheckin({ ...values, files: [...files], file: files[0], name: files.map(file => file.name).join(', ') })
        this.files = []; this.close(true)
      } catch (error) { this.error = error.message }
    },
    async attachFiles() {
      if (!this.ready || this.busy || this.appendUncertain || !this.files.length) return
      const names = this.files.map(file => file.name.toLocaleLowerCase())
      if (new Set(names).size !== names.length || this.existingFiles.some(file => names.includes(file.filename.toLocaleLowerCase()))) {
        this.error = 'Choose file names that are not already in the snapshot'; return
      }
      const request = this.request, scope = this.scope
      this.busy = true; this.error = ''; let committing = false
      try {
        const paths = []
        for (const file of this.files) {
          paths.push(await uploadFormFile(scope.ticket, scope.project, file))
          if (request !== this.request) return
        }
        committing = true
        await rpc('add_file', [scope, this.appendSnapshot.code, paths], { file_type:'attachment', mode:'upload' })
        if (request !== this.request) return
        this.busy = false; this.files = []; this.close(true); this.$emit('attached')
      } catch (error) {
        if (request === this.request) { this.appendUncertain = committing && (!error.status || error.status >= 500); this.error = error.message }
      } finally { if (request === this.request) this.busy = false }
    },
  },
}
</script>
<template>
  <Teleport to="body">
    <dialog ref="dialog" class="record-dialog object-checkin" :aria-label="t(title)" @cancel.prevent="close()" @paste="paste" @dragover.prevent @drop.prevent="addFiles($event.dataTransfer.files)">
      <header><AppButton v-if="mobile" label="Back" icon="MDI_ARROW_LEFT" icon-only @click="close()" /><div><h2>{{ t(title) }}</h2><small>{{ owner?.name || owner?.title || owner?.code }}<template v-if="!mobile"> · {{ owner?.__search_key__ }}</template></small></div><AppButton v-if="!mobile" label="Close" icon="close" @click="close()" /></header>
      <p v-if="busy" role="status">{{ t('Loading data…') }}</p><p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <form @submit.prevent="submit">
        <div class="object-checkin-body">
        <AppSelect v-if="!revision && !appendSnapshot" v-model="repositoryAlias" :options="repositories" :translate-labels="false" label="Repository" :disabled="busy" />
        <label v-if="!preview">{{ t('Process') }}<AppSelect v-model="process" :options="processes" :translate-labels="false" label="Process" :disabled="busy || revision || !!appendSnapshot" @update:model-value="context = ''" /></label>
        <label v-if="!preview">{{ t('Context') }}<input v-model="context" :disabled="busy || revision || !!appendSnapshot" maxlength="256"></label>
        <label v-if="!appendSnapshot">{{ t('Description') }}<textarea v-model="description" rows="3" :disabled="busy"></textarea></label>
        <input ref="fileInput" type="file" multiple hidden :accept="preview ? 'image/*' : undefined" @change="addFiles($event.target.files); $event.target.value = ''">
        <div class="configuration-actions checkin-file-actions"><AppButton label="Choose files for check-in" icon="upload" :disabled="busy" @click="$refs.fileInput.click()" /><AppButton label="Save from Clipboard" icon="MDI_CONTENT_PASTE" :icon-only="mobile" :disabled="busy" @click="readImage" /></div>
        <p v-if="!files.length && !mobile" class="muted">{{ t('Drop files here, paste an image, or choose files for check-in.') }}</p>
        <ul class="file-preview-files"><li v-for="(file, index) in files" :key="index"><span>{{ file.name }} · {{ file.size }} {{ t('bytes') }}</span><AppButton label="Remove file" icon="close" icon-only @click="files.splice(index, 1)" /></li></ul>
        <label v-if="files.length > 1 && !appendSnapshot">{{ t('Check in multiple files?') }}<AppSelect v-model="mode" label="Check in multiple files?" :options="[{ value: 'group', label: 'One group' }, { value: 'individual', label: 'Separately' }]" /></label>
        <SettingRow v-if="!appendSnapshot" title="Keep original file names" :control-id="formId + '-keep-file-name'"><AppSwitch :id="formId + '-keep-file-name'" v-model="keepFileName" label="Keep original file names" /></SettingRow>
        <template v-if="revision"><p class="notice">{{ t('The file stored in this revision will be replaced. Use Save snapshot when you need a new version.') }}</p><SettingRow title="Replace revision" :control-id="formId + '-replace-revision'"><AppSwitch :id="formId + '-replace-revision'" v-model="confirmed" label="Replace revision" /></SettingRow></template>
        <p v-if="appendUncertain" class="notice" role="alert">{{ t('The attachment result is unknown. Close this window and refresh the snapshot before retrying.') }}</p>
        <div v-if="discard" class="notice" role="alert"><p>{{ t('Discard unsaved changes?') }}</p><AppButton label="Continue editing" @click="discard = false" /><AppButton label="Discard" destructive @click="close(true)" /></div>
        </div>
        <footer><AppButton label="Cancel" :disabled="busy" @click="close()" /><AppButton type="submit" :label="appendSnapshot ? 'Attach files' : 'Add to Commit Queue'" icon="save" highlighted :disabled="!ready || busy || appendUncertain || !files.length || !(context.trim() || process) || revision && !confirmed || !appendSnapshot && !queueCheckin" /></footer>
      </form>
    </dialog>
  </Teleport>
</template>
<style>
.object-checkin-body { display:contents; }
@media(max-width:700px) {
  .object-checkin.record-dialog[open] { display:flex; flex-direction:column; width:100dvw; height:100dvh; max-width:none; max-height:100dvh; margin:0; padding:0; border:0; border-radius:0; overflow:hidden; gap:0; }
  .object-checkin > header { flex:none; display:flex; flex-wrap:nowrap; gap:8px; padding:8px; margin:0; }
  .object-checkin > header > div { flex:1; min-width:0; }
  .object-checkin > header h2 { font-size:var(--text-body-large); margin:0; }
  .object-checkin > header small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--muted); }
  .object-checkin > header .icon-button { width:28px; height:28px; min-width:28px; }
  .object-checkin > :is(p,.notice) { flex:none; margin:4px 8px; }
  .object-checkin > form { display:flex; flex-direction:column; flex:1; min-height:0; margin:0; }
  .object-checkin .object-checkin-body { display:flex; flex-direction:column; flex:1; min-height:0; overflow:auto; overscroll-behavior:contain; gap:8px; padding:8px 12px; }
  .object-checkin-body > label { display:flex; flex-direction:column; gap:4px; font-size:var(--text-label); }
  .object-checkin .checkin-file-actions { display:flex; flex-wrap:nowrap; gap:6px; margin:0; }
  .checkin-file-actions > .app-button:first-child { flex:1; min-width:0; min-height:36px; font-size:var(--text-label); padding:6px 8px; }
  .checkin-file-actions > .icon-button { flex:none; width:36px; height:36px; min-width:36px; }
  .object-checkin .settings-row { display:flex; align-items:center; gap:8px; padding:4px 0; min-height:32px; }
  .object-checkin .setting-description { flex:1; min-width:0; }
  .object-checkin .setting-description strong { font-size:var(--text-label); font-weight:400; }
  .object-checkin .setting-control { flex:none; width:auto; }
  .object-checkin form > footer { display:flex; flex:none; gap:8px; margin:0; padding:8px 12px max(8px,env(safe-area-inset-bottom)); border:0; background:var(--surface-high); }
  .object-checkin form > footer > .app-button { min-height:36px; font-size:var(--text-label); padding:6px 10px; }
  .object-checkin form > footer > .app-button:last-child { flex:1; min-width:0; }
}
</style>
