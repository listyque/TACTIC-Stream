<script>
// SearchQuickFilterPopup.qml / SearchAssigneeFilterPopup.qml; the tab owns selection.
import { nextTick, toRaw } from 'vue'
import { searchConfiguration, userProfile } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppMenu from '../../controls/AppMenu.vue'
import UserPicker from '../../controls/UserPicker.vue'
import QuickFilterOptions from './QuickFilterOptions.vue'

const mine = '__current_login__'
export default {
  components: { AppButton, AppIcon, AppMenu, UserPicker, QuickFilterOptions },
  props: { ticket: String, project: String, searchType: String, tabId: String, scope: String, login: String, selections: Object, layout: Object, disabled: Boolean, boundary: Object, overlay: Boolean },
  emits: ['apply', 'reset', 'edit', 'toggle'],
  data() { return { catalog: null, busy: false, error: '', request: 0, visible: false, top: 0, height: 0, flows: {}, menuBoundary: null, users: null, usersBusy: false, usersError: '', usersRequest: 0 } },
  computed: {
    context() { return [this.ticket, this.project, this.searchType, this.tabId, this.scope] },
    count() { return Object.values(this.selections || {}).reduce((count, values) => count + values.length, 0) },
    groups() {
      if (!this.catalog) return []
      const standard = new Map(this.catalog.configuration.groups.map(group => [group.key, group]))
      const personal = new Map((this.layout?.groups || []).map(group => [group.key, group]))
      const catalog = [...this.catalog.groups]
      for (const key of Object.keys(this.selections || {})) if (key.startsWith('column:') && !catalog.some(group => group.key === key))
        catalog.push({ key, title: key.slice(7).replaceAll('_', ' '), source: 'column', options: [] })
      const order = [...personal.keys(), ...standard.keys(), ...catalog.map(group => group.key)]
      return [...new Set(order)].flatMap(key => {
        const group = catalog.find(group => group.key === key), base = standard.get(key) || {}, local = personal.get(key) || {}
        if (!group || base.enabled === false || local.enabled === false) return []
        const values = this.selections?.[key] || []
        const allowed = value => (!base.options || base.options.includes(value)) && (!local.options || local.options.includes(value))
        const options = [...group.options, ...values.filter(value => !group.options.some(option => option.key === value)).map(value => ({ key: value, title: value }))].filter(option => allowed(option.key))
        return [{ ...group, options, values }]
      })
    },
    selectedUsers() { return (this.selections?.assigned || []).filter(value => value !== mine) },
    personalized() { return this.layout !== null && this.layout !== undefined },
  },
  watch: {
    context() { this.request++; this.usersRequest++; this.busy = this.usersBusy = false; this.catalog = null; this.users = null; this.error = this.usersError = ''; this.$refs.menu.close(); this.$refs.assignees.close() },
  },
  mounted() {
    this.menuBoundary = this.boundary || this.$el.closest('.workspace-browser')
    this.resize = new ResizeObserver(this.scrolled); this.resize.observe(this.$refs.viewport)
  },
  beforeUnmount() { this.request++; this.usersRequest++; this.resize.disconnect() },
  methods: {
    t,
    open() { this.$refs.menu.open = true },
    close() { this.$refs.menu.close(true) },
    async toggled(event) {
      this.$emit('toggle', event)
      this.visible = event.target.open
      if (!this.visible) return
      this.$refs.viewport.scrollTop = 0; await this.load(); await nextTick(); this.scrolled()
    },
    async load(force = false) {
      if (this.busy || this.catalog && !force) return
      const request = ++this.request
      this.busy = true; this.error = ''
      try {
        const catalog = await searchConfiguration('read', this.ticket, this.project, this.searchType, { scope: this.scope || this.searchType.split('?')[0] })
        if (request === this.request) this.catalog = catalog
      } catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
    scrolled() { this.top = this.$refs.viewport.scrollTop; this.height = this.$refs.viewport.clientHeight },
    optionsFor(group) {
      const all = { key: '', title: t('ALL'), selected: !group.values.length, accent: group.accent }
      if (group.key === 'assigned' && group.source === 'task') return [all,
        { key: mine, title: t('MY TASKS'), icon: 'user', accent: group.accent, selected: group.values.includes(mine) },
        { key: '__users__', title: t(this.selectedUsers.length ? 'USERS' : 'SELECT USERS') + (this.selectedUsers.length ? ' / ' + this.selectedUsers.length : ''), icon: 'groups', accent: group.accent, selected: !!this.selectedUsers.length }]
      return [all, ...group.options.map(option => ({ ...option, accent: option.accent || group.accent, marker: option.showAccentMarker ?? !!option.accent, selected: group.values.includes(option.key) }))]
    },
    apply(selections) {
      this.$emit('apply', { groups: structuredClone(toRaw((this.layout || this.catalog.configuration).groups)), defaultSelections: selections })
    },
    select(group, key) {
      if (this.disabled) return
      if (key === '__users__') { this.openUsers(); return }
      const selections = structuredClone(toRaw(this.selections || {})), values = new Set(selections[group] || [])
      if (!key) values.clear(); else if (values.has(key)) values.delete(key); else values.add(key)
      if (values.size) selections[group] = [...values]; else delete selections[group]
      this.apply(selections)
    },
    clear() { if (!this.disabled) this.apply({}) },
    reset() { if (!this.disabled) this.$emit('reset', structuredClone(toRaw(this.catalog.configuration.defaultSelections))) },
    edit() { this.close(); this.$emit('edit', this.catalog) },
    focusGroup(index, direction) {
      const group = this.groups[index], flow = group && this.flows[group.key]
      if (!flow) { this.$refs.viewport.scrollTop = 0; this.scrolled(); this.$refs.edit.$el.focus(); return }
      flow.focusOption(direction > 0 ? 0 : flow.options.length - 1)
    },
    async openUsers() {
      this.$refs.menu.close(); this.$refs.assignees.open = true
      if (this.users || this.usersBusy) return
      const request = ++this.usersRequest
      this.usersBusy = true; this.usersError = ''
      try {
        const result = await userProfile('read', this.ticket, this.project, { login: this.login })
        if (request === this.usersRequest) this.users = result.users
      } catch (error) { if (request === this.usersRequest) this.usersError = error.message }
      finally { if (request === this.usersRequest) this.usersBusy = false }
    },
    setUsers(values) {
      const selections = structuredClone(toRaw(this.selections || {})), selected = [...values]
      if ((selections.assigned || []).includes(mine)) selected.push(mine)
      if (selected.length) selections.assigned = selected; else delete selections.assigned
      this.apply(selections)
    },
  },
}
</script>
<template>
  <div class="search-quick-filter-host">
    <AppMenu ref="menu" class="search-quick-filters" :class="{ 'has-selection':count > 0 }" label="Quick filters" icon="filter" :max-height="400" :show-label="overlay" :overlay="overlay" :close-on-select="false" :boundary="boundary || menuBoundary" @toggle="toggled">
      <template #trigger><AppIcon name="filter" /><span v-if="overlay">{{ t('Quick filters') }}</span><small v-if="count" class="action-count">{{ count }}</small></template>
      <div ref="viewport" class="quick-filter-viewport" :aria-busy="busy" @scroll.passive="scrolled">
        <header><strong>{{ t('QUICK FILTERS') }}</strong>
          <AppButton v-if="personalized && catalog" icon-only icon="reset" label="Apply the shared default to this tab" :disabled="disabled" @click="reset" />
          <AppButton v-if="count && catalog" icon-only icon="close" label="Clear quick filters" :disabled="disabled" @click="clear" />
          <AppButton ref="edit" label="Edit" icon="edit" tonal :disabled="busy || !catalog" @click="edit" @keydown.shift.tab.prevent="focusGroup(groups.length - 1, -1)" />
        </header>
        <p v-if="busy || error" :class="{ error }" role="status"><span>{{ t(busy ? 'Loading filters…' : error) }}</span><AppButton v-if="error" label="Retry" @click="load(true)" /></p>
        <section v-for="(group, index) in groups" :key="group.key" class="quick-filter-group" :aria-label="group.source === 'task' ? t(group.title) : group.title">
          <h3>{{ group.source === 'task' ? t(group.title) : group.title }}</h3>
          <QuickFilterOptions :ref="flow => flows[group.key] = flow" :options="optionsFor(group)" :viewport="$refs.viewport" :top="top" :height="height" :active="visible" :disabled="disabled"
            @activate="select(group.key, $event)" @scroll="scrolled" @adjacent="focusGroup(index + $event, $event)" />
        </section>
        <p v-if="catalog && !groups.length && !busy && !error" class="muted">{{ t('No filters available') }}</p>
        <slot :close="close" />
      </div>
    </AppMenu>
    <AppMenu ref="assignees" class="quick-filter-assignees" label="ASSIGNED TO" icon="groups" :overlay="overlay" :anchor="$refs.menu?.$el.querySelector('summary')" :close-on-select="false" :boundary="boundary || menuBoundary" @toggle="$emit('toggle', $event)">
      <div class="quick-assignee-body">
        <header><strong>{{ t('ASSIGNED TO') }}</strong><AppButton class="quick-filter-chip" :highlighted="!(selections?.assigned || []).length" label="ALL" :disabled="disabled" @click="select('assigned', '')" /></header>
        <AppButton class="quick-filter-chip" icon="user" label="MY TASKS" :highlighted="(selections?.assigned || []).includes('__current_login__')" :disabled="disabled" @click="select('assigned', '__current_login__')" />
        <hr>
        <p v-if="usersBusy || usersError" role="status"><span>{{ t(usersBusy ? 'Loading data…' : usersError) }}</span><AppButton v-if="usersError" label="Retry" @click="openUsers" /></p>
        <UserPicker v-if="users" :users="users" :current-login="login" :model-value="selectedUsers" :disabled="disabled" @update:model-value="setUsers" />
      </div>
    </AppMenu>
  </div>
</template>
<style>
.search-quick-filter-host { position:relative; }
.search-quick-filters:not(.labelled-menu) > summary { width:38px; height:38px; }
.search-quick-filters.has-selection > summary, .search-quick-filters[open] > summary { color:var(--primary); }
.search-quick-filters[open] > summary { background:var(--content-selection); }
.workspace-menu.search-quick-filters > .account-panel { width:440px; max-height:min(400px, calc(100dvh - 16px)); padding:0; display:flex; flex-direction:column; overflow:hidden; transition:none; }
.quick-filter-viewport { position:relative; min-height:0; overflow:auto; overscroll-behavior:contain; scrollbar-gutter:stable; padding:12px; }
.quick-filter-viewport > header { display:flex; align-items:center; gap:8px; min-height:var(--control-height); }
.quick-filter-viewport > header > strong { flex:1; font-size:12px; }
.quick-filter-viewport > header > .icon-button { width:28px; height:28px; }
.quick-filter-viewport > header > .app-button:not(.icon-button) { flex:none; padding:0 12px; font-size:var(--text-body); font-weight:600; color:var(--on-surface); border:1px solid var(--outline-variant); background:var(--hover); border-radius:var(--button-radius); min-height:var(--control-height); }
.quick-filter-group { margin-top:16px; }
.quick-filter-group > h3 { margin:0 0 9px; font-size:var(--text-body-large); font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.quick-filter-options { position:relative; }
.quick-filter-options .quick-filter-chip.app-button { gap:5px; }
.quick-filter-options .quick-filter-chip .app-icon { width:11px; height:11px; font-size:11px; color:var(--muted); }
.quick-filter-options .primary .app-icon { color:var(--on-selected); }
.quick-filter-accent { width:8px; height:8px; flex:none; border-radius:50%; background-color:var(--chip-accent); }
.quick-filter-assignees > summary { display:none; }
.workspace-menu.quick-filter-assignees > .account-panel { width:400px; height:430px; max-height:calc(100dvh - 16px); padding:12px; overflow:hidden; }
.quick-assignee-body { display:flex; flex-direction:column; gap:10px; min-height:0; }
.quick-assignee-body > header { display:flex; align-items:center; gap:8px; }
.quick-assignee-body > header strong { flex:1; font-size:var(--text-body-large); }
.quick-assignee-body > .quick-filter-chip { align-self:flex-start; }
.quick-assignee-body > hr { width:100%; margin:0; border:0; border-top:1px solid var(--outline-variant); }
.quick-filter-field { margin-top:16px; border-top:1px solid var(--outline-variant); padding-top:12px; }
.quick-filter-field > summary { min-height:28px; }
.quick-filter-field .search-filter-panel { display:grid; gap:12px; padding-top:12px; }
.quick-filter-field .search-filter-panel > label { display:grid; gap:6px; padding:0; }
</style>
