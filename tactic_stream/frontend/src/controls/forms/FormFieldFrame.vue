<script setup>
import AppIcon from '../AppIcon.vue';
import { t } from '../../i18n.js';
import { ref, onMounted, onBeforeUnmount } from 'vue';
defineProps({
  title: String,
  fieldName: String,
  description: String,
  icon: String,
  error: String,
  required: Boolean,
  readonly: Boolean
});
const heading = ref(null),
  editor = ref(null),
  weights = ref({ heading: 1, editor: 1 });
let observer;
onMounted(() => {
  observer = new ResizeObserver(() => {
    weights.value = {
      heading: Math.max(1, heading.value.offsetHeight),
      editor: Math.max(1, editor.value.offsetHeight)
    };
  });
  observer.observe(heading.value);
  observer.observe(editor.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <section class="form-field-frame" :class="{ 'has-error': !!error }">
    <div
      class="form-field-layout"
      :style="{
        '--field-heading-weight': weights.heading + 'fr',
        '--field-editor-weight': weights.editor + 'fr'
      }"
    >
      <header ref="heading">
        <span class="form-field-icon"><AppIcon :name="icon" /></span>
        <div>
          <strong
            ><span class="field-title-text">{{ t(title) }}</span
            ><span v-if="required" class="field-required"> *</span></strong
          >
          <p>{{ description ? t(description) : fieldName }}</p>
          <small v-if="readonly">{{ t('Read only') }}</small>
        </div>
      </header>
      <div ref="editor" class="form-field-editor">
        <slot />
        <p v-if="error" role="alert">{{ t(error) }}</p>
      </div>
    </div>
  </section>
</template>

<style>
.form-field-frame {
  container-type: inline-size;
  min-width: 0;
  background: var(--surface);
  border-radius: var(--surface-radius);
  box-shadow: inset 0 0 0 1px var(--outline-variant);
}
.form-field-frame.has-error {
  box-shadow: inset 0 0 0 1px var(--error);
}
.form-field-layout {
  height: 100%;
  display: grid;
  grid-template-columns: var(--form-field-label-width) minmax(0, 1fr);
  column-gap: var(--form-field-column-spacing);
  row-gap: var(--form-field-row-spacing);
  padding: var(--form-field-padding);
  align-items: start;
}
.form-field-layout > header {
  display: flex;
  align-items: start;
  gap: var(--form-field-label-spacing);
  min-width: 0;
}
.form-field-icon {
  display: grid;
  place-items: center;
  flex: none;
  width: var(--form-field-icon-extent);
  height: var(--form-field-icon-extent);
  border-radius: var(--item-radius);
  background: var(--secondary-container);
  color: var(--primary);
}
.form-field-icon > .app-icon {
  width: var(--form-field-icon-size);
  height: var(--form-field-icon-size);
  font-size: var(--form-field-icon-size);
}
.form-field-layout > header > div {
  display: flex;
  flex-direction: column;
  gap: var(--form-field-text-spacing);
  min-width: 0;
  flex: 1;
}
.form-field-layout header strong {
  display: flex;
  gap: 4px;
  font-size: var(--font-body-large-size);
  line-height: var(--font-body-large-line-height);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.form-field-layout .field-title-text {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}
.form-field-layout header :is(p, small) {
  font-size: var(--font-caption-size);
  line-height: var(--font-caption-line-height);
  margin: 0;
  color: var(--muted);
  overflow-wrap: anywhere;
}
.form-field-layout header small {
  font-weight: 600;
}
.field-required {
  color: var(--error);
  font-weight: 700;
}
.form-field-editor {
  display: flex;
  flex-direction: column;
  gap: var(--form-field-editor-spacing);
  min-width: 0;
}
.form-field-editor > p {
  color: var(--error);
  font-size: var(--font-caption-size);
  line-height: var(--font-caption-line-height);
  margin: 0;
  overflow-wrap: anywhere;
}
.form-field-frame.has-error .form-field-icon {
  color: var(--error);
  background: var(--error-container);
}
.form-field-frame.has-error header strong {
  color: var(--error);
}
@container (max-width:699px) {
  .form-field-layout {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(min-content, var(--field-heading-weight)) minmax(
        min-content,
        var(--field-editor-weight)
      );
  }
}
</style>
