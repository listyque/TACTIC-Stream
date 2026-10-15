<script>
// Handler ProjectChooser, ProjectModel filtering and ProjectCard.
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import ItemPreview from '../../controls/ItemPreview.vue'

export default {
  components: { AppButton, AppCheckbox, ItemPreview },
  props: { projects: Array, selected: String, inline: Boolean }, emits: ['selected'],
  data() { return { showRetired: false, showTemplates: false, showBuiltins: false } },
  computed: {
    filters() { return [['showRetired', 'Retired', this.projects.filter(this.retired).length], ['showTemplates', 'Templates', this.projects.filter(this.template).length], ['showBuiltins', 'Built-in', this.projects.filter(item => item.__builtin__).length]] },
    visibleProjects() { return this.projects.filter(item => item.__builtin__ ? this.showBuiltins : this.template(item) ? this.showTemplates : this.showRetired || !this.retired(item)) },
    groups() {
      const groups = new Map()
      for (const project of this.visibleProjects) { const category = project.category || ''; if (!groups.has(category)) groups.set(category, []); groups.get(category).push(project) }
      return [...groups].map(([title, projects]) => ({ title, projects }))
    },
  },
  methods: {
    t,
    retired(item) { return String(item.s_status || '').toLowerCase() === 'retired' },
    template(item) { return item.is_template === true || item.is_template === 1 || ['true', 't', '1'].includes(String(item.is_template).toLowerCase()) },
    initials(item) { return (item.title || item.code).replaceAll('_', ' ').split(/\s+/).filter(Boolean).slice(0, 2).map(word => word[0]).join('').toUpperCase() },
    lifecycle(item) { return item.__builtin__ ? 'BUILT-IN' : this.template(item) ? 'TEMPLATE' : this.retired(item) ? 'ARCHIVED' : 'ACTIVE' },
    close() { if (!this.inline) this.$refs.popup.hidePopover() },
    choose(code) { this.$emit('selected', code); this.close() },
  },
}
</script>

<template>
  <div ref="popup" :id="inline ? undefined : 'project-chooser'" class="project-chooser" :class="{ 'project-catalog-inline':inline }" :popover="inline ? undefined : 'auto'" :role="inline ? 'region' : 'dialog'" :aria-label="t('Projects')" @keydown.esc.stop>
    <header v-if="!inline"><div><h2>{{ t('Projects') }}</h2><p class="muted" role="status">{{ t('{visible} of {total} projects shown', { visible: visibleProjects.length, total: projects.length }) }}</p></div><AppButton autofocus icon-only label="Close" icon="close" @click="close" /></header>
    <div class="project-filters"><AppCheckbox v-for="[key, label, count] in filters" :key="key" :model-value="$data[key]" :label="label" @update:model-value="$data[key] = $event"><span>{{ t(label) }} · {{ count }}</span></AppCheckbox></div>
    <div class="project-categories" tabindex="0" :aria-label="t('Available projects')">
      <section v-for="group in groups" :key="group.title"><h3>{{ group.title || t('No Category') }} · {{ group.projects.length }}</h3><div class="project-cards">
        <AppButton v-for="item in group.projects" :key="item.code" class="project-card" :data-project="item.code" :aria-label="item.title || item.code" :aria-pressed="item.code === selected" :title="item.title || item.code" @click="choose(item.code)">
          <ItemPreview :source="item.preview" :fallback-text="initials(item)" />
          <span class="project-card-heading"><strong>{{ item.title || item.code }}</strong><span class="project-lifecycle" :class="{ retired: retired(item), builtin: item.__builtin__ }">{{ t(lifecycle(item)) }}</span></span>
          <span class="project-description muted">{{ item.description || t('No project description') }}</span>
          <span class="project-card-details"><span class="muted">{{ t('Category') }}</span><span>{{ item.category || t('Not set') }}</span><span class="muted">{{ t('Type') }}</span><span>{{ item.type || t('Not set') }}</span></span>
        </AppButton>
      </div></section>
      <p v-if="!groups.length" class="muted project-empty">{{ t('No projects match the current filters') }}</p>
    </div>
  </div>
</template>
