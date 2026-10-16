<script>
import { t } from '../i18n.js';
import AppButton from './AppButton.vue';
import ItemPreview from './ItemPreview.vue';
import { readPreviewImage } from './previewImage.js';
import { controls } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';

export default {
  components: { AppButton, ItemPreview },
  props: {
    modelValue: File,
    displayFile: File,
    previewUrl: String,
    fallbackText: String,
    accent: String,
    disabled: Boolean
  },
  emits: ['update:modelValue', 'validating'],
  data() {
    return {
      loading: false,
      error: '',
      selection: 0,
      actionsHeight: 36,
      actionsWidth: 1,
      previewSize: controls.imagePicker.previewSize
    };
  },
  mounted() {
    this.resize = new ResizeObserver(() => {
      this.actionsHeight = this.$refs.actions.offsetHeight;
      this.actionsWidth = this.$refs.actions.offsetWidth;
    });
    this.resize.observe(this.$refs.actions);
  },
  beforeUnmount() {
    this.selection++;
    this.resize?.disconnect();
  },
  methods: {
    t,
    async choose(event) {
      const file = event.target.files[0];
      event.target.value = '';
      if (!file) return;
      const selection = ++this.selection;
      this.loading = true;
      this.$emit('validating', true);
      this.error = '';
      try {
        await readPreviewImage(file);
        if (selection === this.selection) {
          this.loading = false;
          this.$emit('validating', false);
          if (!this.disabled) this.$emit('update:modelValue', file);
        }
      } catch {
        if (selection === this.selection)
          this.error = 'The selected preview is not a readable image';
      } finally {
        if (selection === this.selection) {
          this.loading = false;
          this.$emit('validating', false);
        }
      }
    }
  }
};
</script>

<template>
  <div class="image-picker" :aria-busy="loading">
    <div
      class="image-picker-layout"
      :style="{
        '--image-actions-height': actionsHeight + 'fr',
        '--image-actions-width': actionsWidth + 'fr',
        '--image-preview-weight': previewSize + 'fr'
      }"
    >
      <ItemPreview
        :file="modelValue || displayFile"
        :source="previewUrl"
        :fallback-text="fallbackText"
        :accent="accent || 'var(--primary)'"
        :preview-size="previewSize"
        outlined
        fill-mode="contain"
      />
      <div ref="actions" class="image-picker-actions">
        <slot />
        <input
          ref="file"
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif,image/bmp"
          hidden
          :disabled="disabled || loading"
          :aria-label="t('Choose preview image')"
          @change="choose"
        />
        <AppButton
          label="Choose image"
          icon="add-photo-alternate"
          :disabled="disabled || loading"
          @click="$refs.file.click()"
        />
        <AppButton
          v-if="modelValue"
          label="Undo image selection"
          icon="undo"
          :disabled="disabled || loading"
          @click="
            error = '';
            $emit('update:modelValue', null);
          "
        />
        <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      </div>
    </div>
  </div>
</template>

<style>
.image-picker.image-picker {
  display: block;
  container-type: inline-size;
}
.image-picker-layout {
  display: grid;
  grid-template-columns:
    minmax(var(--image-picker-preview-size), var(--image-preview-weight))
    minmax(min-content, var(--image-actions-width));
  column-gap: var(--image-picker-column-spacing);
  row-gap: var(--image-picker-row-spacing);
  align-items: center;
  height: 100%;
}
.image-picker .image-picker-actions {
  width: max-content;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: 5px;
}
@container (max-width:401px) {
  .image-picker-layout {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows:
      minmax(var(--image-picker-preview-size), var(--image-preview-weight))
      minmax(min-content, var(--image-actions-height));
  }
}
</style>
