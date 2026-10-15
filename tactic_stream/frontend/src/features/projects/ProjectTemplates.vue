<script>
import { t } from '../../i18n.js'
import { rpc, uploadFormFile } from '../../api.js'
import AppButton from '../../controls/AppButton.vue'

export default {
  components: { AppButton },
  props: { ticket: String, packages: Array },
  emits: ['changed'],
  data() { return { busy: false, error: '', deletion: null } },
  methods: {
    t,
    open() { this.error = ''; this.deletion = null; this.$refs.dialog.showModal() },
    async run(command, args) {
      this.error = ''
      this.busy = true
      try { return await rpc('execute_cmd', [{ ticket: this.ticket, project: 'admin', language: 'python' }, command, args]) }
      catch (error) { this.error = error.message; return null }
      finally { this.busy = false }
    },
    async install(event) {
      const file = event.target.files[0]
      event.target.value = ''
      if (!file) return
      this.busy = true
      this.error = ''
      try {
        const filename = await uploadFormFile(this.ticket, 'admin', file)
        const result = await this.run('tactic.ui.app.ProjectTemplateInstallCmd', { paths: [filename] })
        if (result) this.$emit('changed')
      } catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
    async download(row) {
      const result = await this.run('tactic.ui.app.ProjectTemplateDownloadCmd', { template_dir: row.path })
      if (!result) return
      const link = document.createElement('a')
      link.href = '/assets/_cache/' + encodeURIComponent(this.ticket) + '/' + encodeURIComponent(result.info.filename)
      link.download = result.info.filename
      link.click()
    },
    async remove() {
      const result = await this.run('tactic.ui.app.ProjectTemplateDeleteCmd', { template: this.deletion.code })
      if (result) { this.deletion = null; this.$emit('changed') }
    },
  },
}
</script>

<template>
  <dialog v-window ref="dialog" class="record-dialog project-templates" :aria-label="t('Manage templates')" @cancel.prevent="!busy && $refs.dialog.close()">
    <header><div><h2>{{ t('Manage templates') }}</h2><p class="muted">{{ t('Install, download or remove template packages. Existing projects are not removed.') }}</p></div><AppButton label="Close" icon="close" :disabled="busy" @click="$refs.dialog.close()" /></header>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <input ref="file" type="file" accept=".zip" hidden :aria-label="t('Template ZIP archive')" :disabled="busy" @change="install">
    <AppButton label="Install template" icon="upload" :disabled="busy" @click="$refs.file.click()" />
    <p v-if="!packages.length" class="muted">{{ t('No installed template packages.') }}</p>
    <div v-for="row in packages" :key="row.path" class="project-template-row"><strong>{{ row.code }}</strong><div class="configuration-actions"><AppButton label="Download" icon="download" :disabled="busy" @click="download(row)" /><AppButton label="Delete" icon="delete" :disabled="busy" @click="deletion = row" /></div></div>
    <div v-if="deletion" class="notice"><p>{{ t('Remove template {code}? Existing projects are not removed.', { code: deletion.code }) }}</p><div class="configuration-actions"><AppButton label="Cancel" :disabled="busy" @click="deletion = null" /><AppButton label="Delete" destructive :disabled="busy" @click="remove" /></div></div>
  </dialog>
</template>
