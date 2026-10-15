<script>
import { t } from '../i18n.js'
import AppIcon from './AppIcon.vue'

export default {
  components: { AppIcon },
  props: { source: String, file: File, fallbackText: String, fallbackIcon: String, accent: String, round: Boolean, outlined: Boolean, previewSize: Number, fillMode:{type:String,default:'cover'} },
  emits:['ready','failed'],
  data() { return { localUrl: '', broken: false, request: 0 } },
  computed: { url() { return this.localUrl || this.source || '' } },
  watch: {
    file: { immediate: true, handler(file) {
      const request = ++this.request
      this.localUrl = ''
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => { if (request === this.request) this.localUrl = reader.result }
      reader.readAsDataURL(file)
    } },
    url() { this.broken = false },
  },
  beforeUnmount() { this.request++ },
  methods: { t },
}
</script>

<template>
  <div class="image-picker-preview item-preview" :class="{ 'round-preview': round, 'outlined-preview': outlined }" :style="{ '--preview-accent': accent || undefined, '--preview-icon-size': previewSize == null ? undefined : (previewSize > 40 ? 22 : 16) + 'px', '--preview-text-size': previewSize == null ? undefined : (previewSize > 40 ? 10 : 8) + 'px' }">
    <img v-if="url && !broken" :src="url" :style="{objectFit:fillMode}" :alt="t('Preview image')" loading="lazy" decoding="async" @load="$emit('ready',$event.target)" @error="broken = true; $emit('failed')">
    <span v-else-if="fallbackText" aria-hidden="true">{{ fallbackText }}</span>
    <AppIcon v-else-if="fallbackIcon" :name="fallbackIcon" />
  </div>
</template>
<style>
.image-picker-preview.item-preview { background:color-mix(in srgb, var(--preview-accent, var(--primary)) 60.606%, black); color:var(--on-selected); border:0; }
.image-picker-preview.item-preview.round-preview { background:color-mix(in srgb, var(--preview-accent, var(--primary)) 74.074%, black); }
.image-picker-preview.outlined-preview { background:color-mix(in srgb, var(--preview-accent, var(--primary)) 74.074%, black); color:var(--on-selected); border:1px solid var(--outline); }
.image-picker-preview.outlined-preview:not(.round-preview) { background:color-mix(in srgb, var(--preview-accent, var(--primary)) 60.606%, black); }
.image-picker-preview > span:not(.app-icon) { font-size:var(--preview-text-size, inherit); }
.image-picker-preview > .app-icon { font-size:var(--preview-icon-size, var(--icon-size)); }
</style>
