<script>
// QuickFilterOptions.qml: exact wrapping with viewport-sized chip rows.
import { nextTick } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { packTagRows, tagRowAt } from './tagCloud.js'

export default {
  components: { AppButton, AppIcon },
  props: { options: Array, viewport: Object, top: Number, height: Number, active: Boolean, disabled: Boolean },
  emits: ['activate', 'adjacent', 'scroll'],
  data() { return { rows: [], contentTop: 0 } },
  computed: {
    layoutKey() { return JSON.stringify(this.options.map(option => [option.title, option.icon, !!option.marker])) },
    extent() { const row = this.rows.at(-1); return row ? row.top + row.height : 0 },
    visibleRows() {
      const top = this.top - this.contentTop, bottom = top + this.height
      if (!this.active || bottom <= 0 || top >= this.extent) return []
      return this.rows.slice(Math.max(0, tagRowAt(this.rows, top) - 1), tagRowAt(this.rows, bottom) + 2)
    },
  },
  watch: { layoutKey() { this.pack() }, active(value) { if (value) nextTick(this.pack) } },
  mounted() {
    this.measure = document.createElement('canvas').getContext('2d')
    this.resize = new ResizeObserver(this.pack)
    this.resize.observe(this.$el); this.resize.observe(this.$refs.sizing); this.resize.observe(this.viewport)
    this.pack()
  },
  beforeUnmount() { this.resize.disconnect() },
  methods: {
    pack() {
      if (!this.active || !this.$el.clientWidth || !this.measure) return
      const style = getComputedStyle(this.$refs.sizing)
      this.measure.font = style.fontWeight + ' ' + style.fontSize + ' ' + style.fontFamily
      this.rows = packTagRows(this.options.map(option => ({ ...option, tag: option.title })), this.$el.clientWidth,
        (text, weight, option) => Math.ceil(this.measure.measureText(text).width) + (option.icon ? 16 : 0) + (option.marker ? 13 : 0), undefined, this.$el.clientWidth)
      nextTick(() => { this.contentTop = this.$el.getBoundingClientRect().top - this.viewport.getBoundingClientRect().top + this.viewport.scrollTop - this.viewport.clientTop })
    },
    async focusOption(index, event) {
      event?.preventDefault()
      if (index < 0 || index >= this.options.length) { this.$emit('adjacent', index < 0 ? -1 : 1); return }
      const row = this.rows.find(row => row.cells.some(cell => cell.index === index))
      if (!row) return
      const top = this.contentTop + row.top
      if (top < this.viewport.scrollTop) this.viewport.scrollTop = top
      else if (top + row.height > this.viewport.scrollTop + this.viewport.clientHeight) this.viewport.scrollTop = top + row.height - this.viewport.clientHeight
      this.$emit('scroll')
      await nextTick()
      this.$el.querySelector('[data-option-index="' + index + '"]')?.focus()
    },
  },
}
</script>
<template>
  <div class="quick-filter-options" :style="{ height: extent + 'px' }">
    <div v-for="row in visibleRows" :key="row.top" class="tag-cloud-row" :style="{ top: row.top + 'px', height: row.height + 'px' }">
      <AppButton v-for="cell in row.cells" :key="cell.index" class="quick-filter-chip" :data-option-index="cell.index"
        :highlighted="options[cell.index].selected" :aria-pressed="!!options[cell.index].selected" :disabled="disabled"
        :aria-label="options[cell.index].title" :title="options[cell.index].title"
        :style="{ width: cell.width + 'px', '--chip-accent': options[cell.index].accent || 'var(--primary)' }"
        @click="$emit('activate', options[cell.index].key)" @keydown.tab="focusOption(cell.index + ($event.shiftKey ? -1 : 1), $event)">
        <span v-if="options[cell.index].marker" class="quick-filter-accent" />
        <AppIcon v-if="options[cell.index].icon" :name="options[cell.index].icon" />
        <span class="tag-label">{{ options[cell.index].title }}</span>
      </AppButton>
    </div>
    <span ref="sizing" class="tag-cloud-sizing quick-filter-chip">ALL</span>
  </div>
</template>
