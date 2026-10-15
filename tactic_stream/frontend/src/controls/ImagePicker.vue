<script>
import { t } from '../i18n.js'
import AppButton from './AppButton.vue'
import ItemPreview from './ItemPreview.vue'
import {readPreviewImage} from './previewImage.js'

export default {
  components: { AppButton, ItemPreview },
  props: { modelValue: File, displayFile: File, previewUrl: String, fallbackText: String, accent: String, disabled: Boolean },
  emits: ['update:modelValue', 'validating'],
  data() { return { loading: false, error: '', selection: 0 } },
  beforeUnmount() { this.selection++ },
  methods: {
    t,
    async choose(event) {
      const file = event.target.files[0]
      event.target.value = ''
      if (!file) return
      const selection = ++this.selection
      this.loading = true
      this.$emit('validating', true)
      this.error = ''
      try {
        await readPreviewImage(file)
        if (selection === this.selection) {
          this.loading = false
          this.$emit('validating', false)
          if (!this.disabled) this.$emit('update:modelValue', file)
        }
      } catch { if (selection === this.selection) this.error = 'The selected preview is not a readable image' }
      finally { if (selection === this.selection) { this.loading = false; this.$emit('validating', false) } }
    },
  },
}
</script>

<template>
  <div class="image-picker" :aria-busy="loading">
    <ItemPreview :file="modelValue || displayFile" :source="previewUrl" :fallback-text="fallbackText" :accent="accent" />
    <div class="image-picker-actions">
      <slot />
      <input ref="file" type="file" accept="image/png,image/jpeg,image/webp,image/gif,image/bmp" hidden :disabled="disabled || loading" :aria-label="t('Choose preview image')" @change="choose">
      <AppButton label="Choose image" icon="add" :disabled="disabled || loading" @click="$refs.file.click()" />
      <AppButton v-if="modelValue" label="Undo image selection" icon="reset" :disabled="disabled || loading" @click="error = ''; $emit('update:modelValue', null)" />
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    </div>
  </div>
</template>
