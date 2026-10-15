<script>
// TacticSearchField.qml: shared input/popup behavior, without server knowledge.
import { nextTick, useId } from 'vue'
import { t } from '../i18n.js'
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'

export default {
  components: { AppButton, AppIcon },
  props: { modelValue: String, placeholder: String, label: String, disabled: Boolean, suggestions: { type: Array, default: () => [] }, error: String, boundary: Object },
  emits: ['update:modelValue', 'search', 'accept', 'open', 'dismiss'],
  setup() { return { listId: useId() } },
  data() { return { opened: false, selected: -1 } },
  watch: {
    suggestions() { this.selected = -1; this.show() },
    error() { this.show() },
    disabled(value) { if (value) this.close() },
  },
  mounted() {
    this.resize = new ResizeObserver(this.position); this.resize.observe(this.$el)
    document.addEventListener('pointerdown', this.outside); window.addEventListener('resize', this.position)
  },
  beforeUnmount() { clearTimeout(this.blurTimer); this.resize.disconnect(); document.removeEventListener('pointerdown', this.outside); window.removeEventListener('resize', this.position) },
  methods: {
    t,
    focus() { this.$refs.input.focus() },
    close() { if (this.$refs.popup?.isConnected) this.$refs.popup.hidePopover(); this.opened = false; this.selected = -1 },
    outside(event) { if (!this.$el.contains(event.target)) this.close() },
    blurred() { clearTimeout(this.blurTimer); this.blurTimer = setTimeout(() => { if (!this.$el.contains(document.activeElement)) this.close() }, 120) },
    edit(value) { this.close(); this.$emit('update:modelValue', value) },
    async show() {
      await nextTick()
      if (!this.$refs.popup?.isConnected) return
      if (this.disabled || (!this.suggestions.length && !this.error)) { this.close(); return }
      if (document.activeElement !== this.$refs.input) return
      this.$refs.popup.showPopover(); this.opened = true; this.position()
    },
    position() {
      if (!this.opened) return
      const field = this.$el.getBoundingClientRect(), area = this.boundary?.getBoundingClientRect()
      const left = Math.max(0, area?.left || 0), right = Math.min(innerWidth, area?.right ?? innerWidth)
      const top = Math.max(0, area?.top || 0), bottom = Math.min(innerHeight, area?.bottom ?? innerHeight)
      const width = Math.min(Math.max(240, field.width), right - left - 8)
      const desired = this.error ? 50 : this.suggestions.length * 34 + 8
      const below = bottom - field.bottom - 10, above = field.top - top - 10
      const up = below < Math.min(desired, 180) && above > below
      const height = Math.min(desired, Math.max(0, up ? above : below))
      Object.assign(this.$refs.popup.style, { width: width + 'px', maxHeight: height + 'px',
        left: Math.max(left + 4, Math.min(field.left, right - width - 4)) + 'px',
        top: (up ? field.top - height - 6 : field.bottom + 6) + 'px' })
    },
    async key(event) {
      if (event.isComposing) return
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); this.close(); this.$emit('dismiss'); return }
      if (event.key === 'Enter') {
        event.preventDefault()
        if (this.opened && this.selected >= 0) this.choose(this.selected, event.altKey)
        else { this.close(); this.$emit('search') }
      } else if (this.opened && this.suggestions.length && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
        event.preventDefault()
        this.selected = event.key === 'ArrowDown' ? Math.min(this.suggestions.length - 1, this.selected + 1)
          : this.selected <= 0 ? this.suggestions.length - 1 : this.selected - 1
        await nextTick(); this.$refs.popup.querySelector('#' + CSS.escape(this.listId + '-' + this.selected))?.scrollIntoView({ block: 'nearest' })
      }
    },
    choose(index, newTab = false) {
      const record = this.suggestions[index]
      this.close(); this.focus()
      this.$emit(newTab ? 'open' : 'accept', record)
    },
  },
}
</script>

<template>
  <div class="workspace-search app-search-field" role="search" @focusout="blurred">
    <AppIcon name="search" @click="focus(); $refs.input.select()" />
    <input ref="input" type="search" role="combobox" enterkeyhint="search" autocomplete="off" :value="modelValue" :placeholder="placeholder"
      :aria-label="t(label)" aria-autocomplete="list" aria-haspopup="grid" :aria-controls="listId" :aria-expanded="opened"
      :aria-activedescendant="opened && selected >= 0 ? listId + '-' + selected : undefined" :disabled="disabled"
      @input="edit($event.target.value)" @focus="show" @keydown="key">
    <AppButton v-if="modelValue" icon-only label="Clear search" icon="close" :disabled="disabled" @click="edit(''); focus()" />
    <div ref="popup" popover="manual" class="search-suggestions">
      <p v-if="error" role="status">{{ t(error) }}</p>
      <div v-else :id="listId" role="grid" :aria-label="t('Search suggestions')">
        <div v-for="(record, index) in suggestions" :id="listId + '-' + index" :key="index" role="row" class="search-suggestion-row"
          :class="{ selected: selected === index }" :aria-selected="selected === index" @pointerenter="selected = index">
          <div role="gridcell" class="search-suggestion-content"><AppButton :aria-label="record.title" :title="record.title + (record.description ? ' — ' + record.description : '')"
            @pointerdown.prevent @click="choose(index)" @auxclick.prevent="$event.button === 1 && choose(index, true)">
            <AppIcon name="search" /><strong>{{ record.title }}</strong><span>{{ record.description ? '– ' + record.description : '' }}</span><small v-if="record.keyword">#{{ record.keyword }}</small>
          </AppButton></div>
          <div role="gridcell"><AppButton icon-only icon="MDI_OPEN_IN_NEW" label="Open result in new tab" :aria-label="t('Open {title} in new tab', { title: record.title })"
            :disabled="!record.code && record.id == null" @pointerdown.prevent @click="choose(index, true)" /></div>
        </div>
      </div>
    </div>
  </div>
</template>
