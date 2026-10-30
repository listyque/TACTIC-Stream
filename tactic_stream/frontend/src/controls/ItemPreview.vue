<script>
import { t } from '../i18n.js';
import AppIcon from './AppIcon.vue';
import BusyIndicator from './BusyIndicator.vue';
import { frameColors } from '../appearance.js';
import {
  blend,
  cssColor,
  cssRoles,
  readableText
} from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';

let colorProbe;
const variableRoles = Object.fromEntries(
  Object.entries(cssRoles).map(([role, variable]) => [
    'var(' + variable + ')',
    role
  ])
);

export default {
  components: { AppIcon, BusyIndicator },
  props: {
    source: String,
    file: File,
    fallbackText: String,
    fallbackIcon: String,
    foreground: String,
    accent: String,
    round: Boolean,
    outlined: Boolean,
    selected: Boolean,
    loading: Boolean,
    previewSize: Number,
    fillMode: { type: String, default: 'cover' }
  },
  emits: ['ready', 'failed'],
  data() {
    return { localUrl: '', broken: false, request: 0 };
  },
  computed: {
    pending() {
      return this.loading || this.url.startsWith('pending-preview:');
    },
    url() {
      return this.localUrl || this.source || '';
    },
    fallbackPaint() {
      const role = variableRoles[this.accent] || this.accent;
      let accent =
        frameColors.value[role] ||
        frameColors.value.contentAccent ||
        frameColors.value.action;
      let cssAccent = cssColor(accent);
      if (this.accent && !frameColors.value[role]) {
        colorProbe ||= document
          .createElement('canvas')
          .getContext('2d', { willReadFrequently: true });
        colorProbe.clearRect(0, 0, 1, 1);
        colorProbe.fillStyle = '#000000';
        colorProbe.fillStyle = this.accent;
        colorProbe.fillRect(0, 0, 1, 1);
        accent = [...colorProbe.getImageData(0, 0, 1, 1).data].slice(0, 3);
        cssAccent = this.accent;
      }
      const shade = blend(
        accent,
        [0, 0, 0],
        1 - 1 / (this.round ? 1.35 : 1.65)
      );
      return {
        '--preview-accent': cssAccent,
        color: this.foreground || cssColor(readableText(shade))
      };
    }
  },
  watch: {
    file: {
      immediate: true,
      handler(file) {
        const request = ++this.request;
        this.localUrl = '';
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
          if (request === this.request) this.localUrl = reader.result;
        };
        reader.readAsDataURL(file);
      }
    },
    url() {
      this.broken = false;
    }
  },
  beforeUnmount() {
    this.request++;
  },
  methods: { t }
};
</script>

<template>
  <div
    class="image-picker-preview item-preview"
    :class="{
      'round-preview': round,
      'outlined-preview': outlined,
      'selected-preview': selected
    }"
    :aria-busy="pending || undefined"
    :style="{
      ...fallbackPaint,
      '--preview-icon-size':
        previewSize == null ? undefined : (previewSize > 40 ? 22 : 16) + 'px',
      '--preview-text-size':
        previewSize == null ? undefined : (previewSize > 40 ? 10 : 8) + 'px'
    }"
  >
    <img
      v-if="url && !pending && !broken"
      :src="url"
      :style="{ objectFit: fillMode }"
      :alt="t('Preview image')"
      loading="lazy"
      decoding="async"
      @load="$emit('ready', $event.target)"
      @error="
        broken = true;
        $emit('failed');
      "
    />
    <BusyIndicator
      v-else-if="pending"
      running
      :style="{ width: 'min(24px,45%)', height: 'min(24px,45%)' }"
    />
    <span v-else-if="fallbackText" aria-hidden="true">{{ fallbackText }}</span>
    <AppIcon v-else-if="fallbackIcon" :name="fallbackIcon" />
  </div>
</template>
<style>
.image-picker-preview.item-preview {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  background: color-mix(
    in srgb,
    var(--preview-accent, var(--primary)) 60.606%,
    black
  );
  color: var(--on-selected);
  border: 0;
}
.image-picker-preview.item-preview:has(> .app-icon) {
  /* Native ItemPreview masks the image, but lets the fallback glyph overflow. */
  overflow: visible;
}
.image-picker-preview.item-preview.round-preview {
  background: color-mix(
    in srgb,
    var(--preview-accent, var(--primary)) 74.074%,
    black
  );
}
.image-picker-preview.outlined-preview {
  background: color-mix(
    in srgb,
    var(--preview-accent, var(--primary)) 74.074%,
    black
  );
  color: var(--on-selected);
  border: 1px solid var(--outline);
}
.image-picker-preview.outlined-preview:not(.round-preview) {
  background: color-mix(
    in srgb,
    var(--preview-accent, var(--primary)) 60.606%,
    black
  );
}
.image-picker-preview > span:not(.app-icon) {
  font-size: var(--preview-text-size, inherit);
  line-height: normal;
  font-weight: 600;
}
.image-picker-preview > .app-icon {
  font-size: var(--preview-icon-size, var(--icon-size));
}
.image-picker-preview.outlined-preview.selected-preview {
  border-color: var(--on-selected);
}
.image-picker-preview > .busy-indicator {
  flex: none;
}
</style>
