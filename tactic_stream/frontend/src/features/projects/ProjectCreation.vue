<script>
import { nextTick } from 'vue'
import { t } from '../../i18n.js'
import { projectCreationCatalog, rpc, uploadFormFile } from '../../api.js'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import SettingRow from '../../controls/SettingRow.vue'
import ImagePicker from '../../controls/ImagePicker.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import ProjectTemplates from './ProjectTemplates.vue'

function identifier(value) {
  return value.replace(/[?.!@#$%^&*()'",;+=]/g, '').replaceAll(' ', '_').toLowerCase().replace(/[\\_-]+/g, '_')
}

export default {
  inject: ['openHelp'],
  components: { AppButton, AppSelect, AppSwitch, SettingRow, ImagePicker, ItemPreview, ProjectTemplates },
  props: { ticket: String, openProject: Function },
  data() { return { catalog: null, draft: {}, step: 0, busy: false, error: '', image: null, imageValidating: false,
    createdCode: '', uncertain: false, discard: false, context: null } },
  computed: {
    steps() { return [
      { title: 'Details', icon: 'edit', description: 'Project identity and initial settings.' },
      { title: 'Preview Image', icon: 'image', description: 'Optional image used to identify the project.' },
      { title: 'Template', icon: 'folder', description: 'Start empty or copy a server template.' },
      { title: 'Review', icon: 'check', description: 'Check the settings before creating the project.' },
    ] },
    templates() { return [{ value: '_empty', label: t('Empty project') }, ...(this.catalog?.templates || []).map(row => ({ ...row,
      label: row.label + (row.kind === 'file' ? ' (' + t('From file') + ')' : row.kind === 'builtin' ? ' (' + t('Built-in') + ')' : '') }))] },
    themes() { return [{ value: '', label: t('No theme') }, ...(this.catalog?.themes || [])] },
    selectedTheme() { return this.catalog?.themes.find(row => row.value === this.draft.theme) || {} },
    empty() { return this.draft.source === '_empty' },
    dirty() { return !!(this.draft.title || this.draft.code || this.draft.description || this.draft.category || this.image) },
    review() { return [
      ['Project title', this.draft.title], ['Project code', this.draft.code], ['Category', this.draft.category],
      ['Project description', this.draft.description], ['Template', this.templates.find(row => row.value === this.draft.source)?.label],
      ...(this.empty ? [['Namespace', this.draft.namespace || this.draft.code], ['Theme', this.selectedTheme.label || t('No theme')],
        ['Main project', t(this.draft.isMainProject ? 'Yes' : 'No')], ['Use this project as a template', t(this.draft.isTemplate ? 'Yes' : 'No')]] : []),
    ] },
  },
  watch: { ticket() { if (!this.busy) this.$refs.dialog.close() } },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    t,
    beforeUnload(event) { if (this.$refs.dialog.open && (this.busy || this.dirty || this.createdCode || this.uncertain)) { event.preventDefault(); event.returnValue = '' } },
    async open() {
      if (this.$refs.dialog.open) return
      this.context = { ticket: this.ticket, project: 'admin', language: 'python' }
      this.draft = { title: '', code: '', description: '', category: '', namespace: '', source: '_empty', theme: '', isTemplate: false, isMainProject: false }
      this.catalog = this.image = null
      this.step = 0
      this.error = this.createdCode = ''
      this.uncertain = this.discard = false
      this.$refs.dialog.showModal()
      await this.reload()
      await nextTick()
      this.$refs.title?.focus()
    },
    async reload() {
      if (this.busy) return
      this.busy = true
      this.error = ''
      try {
        this.catalog = await projectCreationCatalog(this.context.ticket)
        if (!this.draft.title) this.draft.isMainProject = this.catalog.isMainProject
        if (this.uncertain) {
          if (this.catalog.projectCodes.includes(this.draft.code)) this.createdCode = this.draft.code
          this.uncertain = false
        }
      } catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
    titleChanged() { this.draft.code = identifier(this.draft.title).slice(0, 30) },
    validate() {
      this.draft.code = identifier(this.draft.code.trim())
      if (!this.draft.title.trim() || this.draft.title.length > 100) return 'Project title is required and cannot exceed 100 characters'
      if (!/^[A-Za-z_][A-Za-z0-9_]{0,29}$/.test(this.draft.code)) return 'Project code must use letters, numbers and underscores, must not start with a number, and cannot exceed 30 characters'
      if (!this.createdCode && this.catalog.projectCodes.includes(this.draft.code)) return 'A project with this code already exists, including retired projects'
      if (this.empty && this.draft.namespace && (!/^[A-Za-z_][A-Za-z0-9_]{0,29}$/.test(this.draft.namespace) || ['sthpw', 'prod'].includes(this.draft.namespace))) return 'Invalid or reserved project namespace'
      if (!this.templates.some(row => row.value === this.draft.source)) return 'Select a template or an empty project'
      return ''
    },
    next() { this.error = this.validate(); if (!this.error) this.step++ },
    cancel() { if (!this.busy) { if (this.dirty || this.createdCode || this.uncertain) this.discard = true; else this.$refs.dialog.close() } },
    async finish() {
      if (this.context.ticket !== this.ticket) throw new Error('Connection context changed. Close this form and reopen it before saving.')
      const values = Object.fromEntries(['title', 'description', 'category'].map(key => [key, this.draft[key].trim()]))
      await rpc('update', [this.context, 'sthpw/project?code=' + encodeURIComponent(this.createdCode), values])
      await this.openProject(this.createdCode)
      this.$refs.dialog.close()
    },
    async submit() {
      if (this.busy || this.uncertain || this.imageValidating) return
      if (this.context.ticket !== this.ticket) { this.error = 'Connection context changed. Close this form and reopen it before saving.'; return }
      if (!this.createdCode && (this.error = this.validate())) return
      this.busy = true
      this.error = ''
      let creating = false
      try {
        if (!this.createdCode) {
          const args = { project_code: this.draft.code, project_title: this.draft.title.trim(), project_theme: this.empty ? this.draft.theme : '' }
          let command = 'tactic.command.CreateProjectCmd'
          if (this.empty) Object.assign(args, { project_type: this.draft.namespace || this.draft.code, is_template: this.draft.isTemplate, is_main_project: this.draft.isMainProject })
          else {
            command = 'tactic.command.ProjectTemplateInstallerCmd'
            const [template, ...path] = this.draft.source.split('|')
            Object.assign(args, { template_code: template, force_database: true, ...(path.length ? { path: path.join('|') } : {}) })
          }
          if (this.image) {
            const filename = await uploadFormFile(this.context.ticket, 'admin', this.image)
            const result = await rpc('execute_cmd', [this.context, 'tactic.command.CopyFileToAssetTempCmd', { filename, ticket: this.context.ticket }])
            args.project_image_path = result.info.lib_path
          }
          creating = true
          await rpc('execute_cmd', [this.context, command, args])
          this.createdCode = this.draft.code
          creating = false
        }
        await this.finish()
      } catch (error) {
        this.uncertain = creating
        this.error = this.createdCode ? 'Project created. Retry opening it; creation will not be repeated.' : error.message
      } finally { this.busy = false }
    },
  },
}
</script>

<template>
  <dialog v-window="{kind:'project_wizard'}" ref="dialog" class="configuration-dialog project-creation-dialog" :aria-label="t('Create project')" @cancel.prevent="cancel">
    <div class="configuration-shell project-wizard" :aria-busy="busy">
      <header class="configuration-header">
        <div class="configuration-brand"><h2>{{ t('Create project') }}</h2><small class="muted">{{ 'TACTIC Stream · ' + t('Project settings') }}</small></div>
        <div class="configuration-page-heading"><div><h1>{{ t(steps[step].title) }}</h1><p class="muted">{{ t(steps[step].description) }}</p></div><AppButton icon-only icon="help" label="Project creation help" @click="openHelp('project_creation')" /></div>
      </header>
      <nav class="configuration-navigation" :aria-label="t('Project creation steps')">
        <AppButton v-for="(item, index) in steps" :key="item.title" :label="item.title" :icon="index < step ? 'check' : item.icon" :aria-pressed="step === index" :disabled="busy || !!createdCode || index > step" @click="step = index; error = ''" />
      </nav>
      <div class="configuration-pages"><section class="content project-wizard-page">
        <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
        <div v-if="!catalog || uncertain" class="configuration-group"><p>{{ t(uncertain ? 'The creation result is unknown. Refresh the catalog before trying again.' : 'Loading project templates…') }}</p><AppButton label="Refresh templates" icon="refresh" :disabled="busy" @click="reload" /></div>
        <template v-if="catalog">
          <div v-show="step === 0" class="configuration-group">
            <h2>{{ t('Project details') }}</h2>
            <SettingRow control-id="project-title" title="Project title" description="The title can contain spaces and special characters, up to 100 characters."><input ref="title" id="project-title" v-model="draft.title" maxlength="100" :disabled="busy || !!createdCode" @input="titleChanged"></SettingRow>
            <SettingRow control-id="project-code" title="Project code" description="Use letters, numbers and underscores, up to 30 characters. The code must be unique, including retired projects."><input id="project-code" v-model="draft.code" maxlength="30" :disabled="busy || !!createdCode"></SettingRow>
            <SettingRow control-id="project-category" title="Category"><input id="project-category" v-model="draft.category" :disabled="busy || !!createdCode"></SettingRow>
            <SettingRow control-id="project-description" title="Project description"><textarea id="project-description" v-model="draft.description" rows="4" :disabled="busy || !!createdCode"></textarea></SettingRow>
            <SettingRow control-id="project-namespace" title="Namespace" description="Prefix for new Search Types, for example studio/shot. Leave empty to use the project code. The sthpw and prod namespaces are reserved."><input id="project-namespace" v-model="draft.namespace" maxlength="30" :disabled="busy || !!createdCode || !empty"></SettingRow>
            <SettingRow control-id="project-template" title="Use this project as a template"><AppSwitch id="project-template" v-model="draft.isTemplate" label="Use this project as a template" :disabled="busy || !!createdCode || !empty" /></SettingRow>
            <SettingRow control-id="project-main" title="Main project" description="Use this empty project as the default project. The server may need a restart."><AppSwitch id="project-main" v-model="draft.isMainProject" label="Set as main project" :disabled="busy || !!createdCode || !empty" /><template #description><p>{{ t('Current main project: {title} ({code})', { title: catalog.defaultProject.title || '—', code: catalog.defaultProject.code || '—' }) }}</p></template></SettingRow>
          </div>
          <div v-show="step === 1" class="configuration-group"><h2>{{ t('Preview Image') }}</h2><p class="muted">{{ t('Optional image used to identify the project.') }}</p><ImagePicker v-model="image" :fallback-text="draft.title" :disabled="busy || !!createdCode" @validating="imageValidating = $event" /></div>
          <div v-show="step === 2" class="configuration-group">
            <h2>{{ t('Copy from template') }}</h2><p class="muted">{{ t('Copy the template configuration, or create an empty project. Templates and themes are loaded from your TACTIC server.') }}</p>
            <SettingRow control-id="project-source" title="Template"><AppSelect id="project-source" v-model="draft.source" :options="templates" :translate-labels="false" label="Copy from template" :disabled="busy || !!createdCode" /></SettingRow>
            <div class="configuration-actions"><AppButton label="Manage templates" icon="settings" :disabled="busy" @click="$refs.templates.open()" /><AppButton label="Refresh templates" icon="refresh" :disabled="busy" @click="reload" /></div>
            <p v-if="!empty" class="muted">{{ t('A template supplies its own namespace and configuration. Main-project, namespace, theme and template flags apply only to an empty project.') }}</p>
            <SettingRow v-if="empty" control-id="project-theme" title="Theme" description="A project theme installs server widget configuration. It does not change your personal interface appearance."><AppSelect id="project-theme" v-model="draft.theme" :options="themes" :translate-labels="false" label="Theme" :disabled="busy || !!createdCode" /></SettingRow>
            <ItemPreview v-if="empty && selectedTheme.preview" :source="selectedTheme.preview" :fallback-text="selectedTheme.label" /><p v-if="empty && selectedTheme.description" class="muted">{{ selectedTheme.description }}</p>
          </div>
          <div v-show="step === 3" class="configuration-group"><h2>{{ t('Review') }}</h2><ImagePicker v-if="image" :display-file="image" :fallback-text="draft.title" disabled /><SettingRow v-for="[title, value] in review" :key="title" :title="title"><span class="project-review-value">{{ value || '—' }}</span></SettingRow></div>
        </template>
      </section></div>
      <footer class="project-wizard-footer">
        <div v-if="discard" class="project-discard"><span>{{ t('Discard this project draft?') }}</span><AppButton label="Keep editing" @click="discard = false" /><AppButton label="Discard changes" destructive @click="$refs.dialog.close()" /></div>
        <template v-else><AppButton label="Cancel" :disabled="busy" @click="cancel" /><span class="muted" role="status">{{ busy ? t('Working…') : '' }}</span><div class="configuration-actions"><AppButton v-if="step > 0 && !createdCode" label="Back" icon="previous" :disabled="busy" @click="step--; error = ''" /><AppButton v-if="step < 3" label="Next" icon="next" highlighted :disabled="busy || !catalog || imageValidating" @click="next" /><AppButton v-else :label="createdCode ? 'Retry opening project' : 'Create project'" icon="add" highlighted :disabled="busy || uncertain || imageValidating" @click="submit" /></div></template>
      </footer>
    </div>
    <ProjectTemplates ref="templates" :ticket="context?.ticket" :packages="catalog?.installedTemplates || []" @changed="reload" />
  </dialog>
</template>
