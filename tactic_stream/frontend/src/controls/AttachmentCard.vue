<script setup>
// AttachmentCard.qml: image above a 64px file row, or a compact file row.
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import AppButton from './AppButton.vue';
import AppIcon from './AppIcon.vue';
import ItemPreview from './ItemPreview.vue';
const props = defineProps({
  title: String,
  extension: String,
  previewUrl: String,
  sizeText: String,
  compact: Boolean,
  disabled: Boolean,
  local: Boolean,
  webPreview: { type: Boolean, default: true },
  activationIcon: String,
  activationLabel: String
});
defineEmits(['activated']);
const card = ref(null),
  width = ref(240),
  pixels = ref(null);
const extensionLabel = computed(() =>
  (props.extension || 'FILE').slice(0, 5).toUpperCase()
);
const imageAttachment = computed(() =>
  [
    'JPG',
    'JPEG',
    'PNG',
    'WEBP',
    'GIF',
    'BMP',
    'TIF',
    'TIFF',
    'TGA',
    'EXR',
    'HDR',
    'SVG',
    'HEIC',
    'AVIF'
  ].includes((props.extension || '').toUpperCase())
);
const imageWidth = computed(() =>
  Math.round(
    props.webPreview
      ? Math.min(Math.max(0, width.value - 16), pixels.value?.width || Infinity)
      : Math.max(0, width.value - 16)
  )
);
const imageHeight = computed(() =>
  Math.round(
    Math.min(
      360,
      imageWidth.value *
        (pixels.value ? pixels.value.height / pixels.value.width : 0.56)
    )
  )
);
let observer, resizeFrame;
// Hidden timelines keep their geometry; resize writes follow the observer's layout pass.
watch(
  () => props.previewUrl,
  () => {
    pixels.value = null;
  }
);
function loaded(event) {
  if (!props.compact && event.target.tagName === 'IMG')
    pixels.value = {
      width: event.target.naturalWidth,
      height: event.target.naturalHeight
    };
}
onMounted(() => {
  observer = new ResizeObserver((entries) => {
    const next = Math.round(entries[0].contentRect.width);
    if (next > 0 && Math.abs(next - width.value) > 1) {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => {
        width.value = next;
      });
    }
  });
  observer.observe(card.value.$el);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  cancelAnimationFrame(resizeFrame);
});
</script>
<template>
  <AppButton
    ref="card"
    class="attachment-card"
    :class="{ compact, 'image-attachment': imageAttachment && !compact }"
    :label="activationLabel"
    :disabled="disabled"
    @load.capture="loaded"
    @click="$emit('activated')"
  >
    <ItemPreview
      v-if="imageAttachment && !compact"
      class="attachment-image"
      :style="{ width: imageWidth + 'px', height: imageHeight + 'px' }"
      :source="previewUrl"
      fallback-icon="image"
      outlined
    />
    <span class="attachment-info"
      ><ItemPreview
        v-if="compact || !imageAttachment"
        class="attachment-badge"
        :style="{
          background:
            imageAttachment && previewUrl
              ? 'var(--surface-highest)'
              : 'var(--primary)',
          color: 'var(--on-selected)',
          '--preview-text-size': (extensionLabel.length > 4 ? 8 : 9) + 'px'
        }"
        :source="imageAttachment ? previewUrl : ''"
        :fallback-text="extensionLabel"
        :round="!imageAttachment" /><span
        ><strong>{{ title }}</strong
        ><small>{{
          imageAttachment && !compact
            ? [extensionLabel, sizeText].filter(Boolean).join(' · ')
            : sizeText
        }}</small></span
      ><AppIcon
        :name="activationIcon || (local ? 'MDI_OPEN_IN_NEW' : 'download')"
    /></span>
  </AppButton>
</template>
<style>
.attachment-card.app-button {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
  width: 100%;
  padding: 0;
  border: 0;
  box-shadow: inset 0 0 0 1px var(--outline-variant);
  border-radius: 14px;
  background: var(--surface-high);
  overflow: hidden;
  text-align: left;
}
.attachment-card.app-button:hover:not(:disabled) {
  background: var(--hover);
}
.attachment-card.image-attachment {
  padding-bottom: 1px;
}
.attachment-image.image-picker-preview {
  flex: none;
  min-height: 0;
  margin: 8px 8px 0;
  border-radius: 10px;
}
.attachment-image img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.attachment-info {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 10px;
  height: 64px;
  padding: 0 7px 0 10px;
}
.image-attachment .attachment-info {
  height: 56px;
  padding: 7px 8px 8px 12px;
  gap: 8px;
}
.attachment-info > span:not(.app-icon) {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}
.attachment-info strong,
.attachment-info small {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.attachment-info strong {
  font-size: var(--text-body-large);
  font-weight: 600;
}
.attachment-info small {
  font-size: var(--text-label);
  font-weight: 400;
  color: var(--muted);
}
.attachment-info > .app-icon {
  width: 28px;
  height: 28px;
  font-size: 18px;
  color: var(--on-surface);
  flex-shrink: 0;
}
.attachment-badge.image-picker-preview {
  flex: none;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--primary);
  color: var(--on-selected);
}
.attachment-badge.round-preview {
  border-radius: 22px;
}
.attachment-card .attachment-badge > span:not(.app-icon) {
  font-weight: 700;
}
.attachment-badge img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
