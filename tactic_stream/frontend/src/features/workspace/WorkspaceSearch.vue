<script>
import AppSearchField from '../../controls/AppSearchField.vue'
import { searchConfiguration } from '../../api.js'
import { t } from '../../i18n.js'

export default {
  components: { AppSearchField },
  props: { modelValue: String, placeholder: String, label: {type:String,default:"Search objects"}, disabled: Boolean, ticket: String, project: String, searchType: String, tabId: String, scope: Object },
  emits: ['update:modelValue', 'search', 'accept', 'open', 'dismiss'],
  data() { return { records: [], error: '', request: 0, boundary: null } },
  computed: { context() { return JSON.stringify([this.ticket, this.project, this.searchType, this.tabId, this.scope]) } },
  watch: {
    context() { this.clear() },
    modelValue(value) { if (value !== this.editedText) this.clear() },
    disabled(value) { if (value) this.clear() },
  },
  mounted() { this.boundary = this.$el.closest('.workspace-browser') },
  beforeUnmount() { this.clear() },
  methods: {
    t,
    focus() { this.$refs.field.focus() },
    clear() { clearTimeout(this.timer); this.request++; this.records = []; this.error = ''; this.$refs.field?.close() },
    edit(value) {
      this.clear(); this.editedText = value; this.$emit('update:modelValue', value)
      if (value.trim()) this.timer = setTimeout(() => this.suggest(value), 180)
    },
    async suggest(keyword) {
      const request = this.request
      try {
        const result = await searchConfiguration('suggestions', this.ticket, this.project, this.searchType, { keyword, ...(this.scope ? { nested_scope: this.scope } : {}) }, true)
        if (request === this.request) this.records = result.records
      } catch (error) { if (request === this.request) { this.records = []; this.error = error.message } }
    },
    choose(record, newTab) { this.clear(); this.$emit(newTab ? 'open' : 'accept', record) },
    search() { this.clear(); this.$emit('search') },
  },
}
</script>

<template>
  <AppSearchField ref="field" :model-value="modelValue" :placeholder="placeholder || t(label)" :label="label" :disabled="disabled"
    :suggestions="records" :error="error" :boundary="boundary" @update:model-value="edit" @search="search"
    @accept="choose($event, false)" @open="choose($event, true)" @dismiss="clear(); $emit('dismiss')" />
</template>
