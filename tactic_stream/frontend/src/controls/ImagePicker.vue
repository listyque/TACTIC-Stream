<script>
import { t } from '../i18n.js';
import AppButton from './AppButton.vue';
import ItemPreview from './ItemPreview.vue';
import { readPreviewImage } from './previewImage.js';
import {
  controls,
  textStyles
} from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { qtLabelTextWidth } from './typography/textMetrics.js';

export default {
  components: { AppButton, ItemPreview },
  props: {
    modelValue: File,
    displayFile: File,
    previewUrl: String,
    fallbackText: String,
    accent: String,
    previewSize: { type: Number, default: controls.imagePicker.previewSize },
    statusText: String,
    description: String,
    inlineErrors: { type: Boolean, default: true },
    disabled: Boolean
  },
  emits: ['update:modelValue', 'validating', 'error'],
  watch: {
    error(value) {
      this.$emit('error', value);
    }
  },
  data() {
    return {
      loading: false,
      error: '',
      selection: 0,
      actionsHeight: 36,
      pickerWidth: 0,
      pickerHeight: 0
    };
  },
  mounted() {
    this.resize = new ResizeObserver((entries) => {
      this.actionsHeight = this.$refs.actions.offsetHeight;
      const root = entries.find((entry) => entry.target === this.$el);
      if (root) {
        this.pickerWidth = root.contentRect.width;
        this.pickerHeight = root.contentRect.height;
      }
    });
    this.resize.observe(this.$refs.actions);
    this.resize.observe(this.$el);
  },
  beforeUnmount() {
    this.selection++;
    this.resize?.disconnect();
  },
  computed: {
    previewRowHeight() {
      if (!this.compact) return this.pickerHeight;
      const room = this.pickerHeight - controls.imagePicker.rowSpacing;
      return Math.max(
        this.previewSize,
        Math.round(
          (room * this.previewSize) / (this.previewSize + this.actionsHeight)
        )
      );
    },
    actionsRowHeight() {
      return this.compact
        ? Math.max(
            this.actionsHeight,
            this.pickerHeight -
              controls.imagePicker.rowSpacing -
              this.previewRowHeight
          )
        : this.pickerHeight;
    },
    columns() {
      if (this.compact) return 'minmax(0,1fr)';
      // Qt fills a captioned column; button-only columns keep their preferred-width ratio.
      if (this.statusText || this.description || this.$slots.default)
        return `${this.previewSize}px minmax(0,1fr)`;
      const actions = Math.max(
        this.actionWidth('Choose image'),
        this.modelValue ? this.actionWidth('Undo image selection') : 0
      );
      const room = this.pickerWidth - controls.imagePicker.columnSpacing;
      const preview = Math.max(
        this.previewSize,
        Math.round((room * this.previewSize) / (this.previewSize + actions))
      );
      return `${preview}px minmax(${actions}px,1fr)`;
    },
    rows() {
      if (!this.compact) return '1fr';
      return `${this.previewRowHeight}px minmax(min-content,1fr)`;
    },
    compact() {
      return (
        this.pickerWidth <
        this.previewSize + controls.imagePicker.minimumActionsWidth
      );
    }
  },
  methods: {
    t,
    pixelCentre(rowHeight, contentHeight) {
      const offset = (rowHeight - contentHeight) / 2;
      return { transform: `translateY(${Math.round(offset) - offset}px)` };
    },
    actionWidth(label) {
      const sizing = controls.button;
      const family = getComputedStyle(document.documentElement).fontFamily;
      const text = qtLabelTextWidth(
        t(label),
        `600 ${textStyles.body}px ${family}`
      );
      return Math.max(
        sizing.minimumWidth,
        Math.ceil(text) +
          sizing.iconSize +
          sizing.spacing +
          sizing.iconPadding +
          sizing.padding
      );
    },
    actionStyle(label) {
      return { width: this.actionWidth(label) + 'px' };
    },
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
  <div
    class="image-picker"
    :class="{ 'image-picker-compact': compact }"
    :aria-busy="loading"
    :style="{ '--image-picker-preview-size': previewSize + 'px' }"
  >
    <div
      class="image-picker-layout"
      :style="{ gridTemplateColumns: columns, gridTemplateRows: rows }"
    >
      <ItemPreview
        data-image-picker-part="Preview"
        :style="pixelCentre(previewRowHeight, previewSize)"
        :file="modelValue || displayFile"
        :source="previewUrl"
        :fallback-text="fallbackText"
        :accent="accent || 'var(--primary)'"
        :preview-size="previewSize"
        outlined
        fill-mode="cover"
      />
      <div
        ref="actions"
        class="image-picker-actions"
        :style="pixelCentre(actionsRowHeight, actionsHeight)"
      >
        <p v-if="statusText" class="image-picker-status">{{ t(statusText) }}</p>
        <p v-if="description" class="image-picker-description">
          {{ t(description) }}
        </p>
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
          data-image-picker-part="ChoosePreview"
          label="Choose image"
          :style="actionStyle('Choose image')"
          icon="add-photo-alternate"
          :disabled="disabled || loading"
          @click="$refs.file.click()"
        />
        <AppButton
          data-image-picker-part="CancelPreview"
          v-if="modelValue"
          label="Undo image selection"
          :style="actionStyle('Undo image selection')"
          icon="undo"
          :disabled="disabled || loading"
          @click="
            error = '';
            $emit('update:modelValue', null);
          "
        />
        <p v-if="error && inlineErrors" class="error" role="alert">
          {{ t(error) }}
        </p>
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
  grid-template-columns: var(--image-picker-preview-size) minmax(0, 1fr);
  column-gap: var(--image-picker-column-spacing);
  row-gap: var(--image-picker-row-spacing);
  align-items: center;
  height: 100%;
}
.image-picker-layout > .item-preview {
  width: var(--image-picker-preview-size);
  height: var(--image-picker-preview-size);
}
.image-picker .image-picker-actions {
  width: 100%;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: 5px;
}
.image-picker-status {
  font-size: 13px;
  line-height: var(--font-body-line-height);
}
.image-picker-description {
  font-size: 12px;
  line-height: var(--font-secondary-line-height);
  color: var(--muted);
}
.image-picker .image-picker-actions > p {
  flex-basis: auto;
  margin: 0;
}
.image-picker-actions .app-button > span {
  overflow: visible;
}
</style>
