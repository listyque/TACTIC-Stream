<script setup>
// Native transaction_log-conf.xml Details -> log -> XmlWdg, without HTML runtime.
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { transactionDetails } from '../../api.js';
import { t } from '../../i18n.js';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/documentation/journal.ui.mjs';
import CodeBlock from '../../controls/CodeBlock.vue';
import { copyText } from '../../controls/clipboard.js';

const props = defineProps({
  ticket: String,
  project: String,
  searchKey: String
});
const xml = ref(''),
  hidden = ref(0),
  busy = ref(false),
  error = ref(''),
  message = ref('');
const host = ref(null),
  width = ref(600);
const scene = computed(() =>
  UI.describe(
    {
      xml: xml.value,
      busy: busy.value,
      error: error.value,
      message: message.value,
      hidden: hidden.value
    },
    width.value,
    appearance.language
  )
);
let observer;
onMounted(() => {
  observer = observeFrameSizes(
    () => (width.value = frameContentWidth(host.value))
  );
  observer.observe(host.value);
});
let request = 0;
async function load() {
  const token = ++request;
  busy.value = true;
  error.value = '';
  xml.value = '';
  message.value = '';
  hidden.value = 0;
  try {
    const result = await transactionDetails(
      props.ticket,
      props.project,
      props.searchKey
    );
    if (token !== request) return;
    xml.value = result.xml;
    hidden.value = result.hidden;
  } catch (failure) {
    if (token === request) error.value = failure.message;
  } finally {
    if (token === request) busy.value = false;
  }
}
async function copy() {
  const turn = request;
  try {
    await copyText(xml.value);
    if (turn === request) message.value = 'Copied to clipboard';
  } catch {
    if (turn === request)
      error.value = 'Clipboard access failed. Select and copy the text below.';
  }
}
watch(() => [props.ticket, props.project, props.searchKey], load, {
  immediate: true
});
onBeforeUnmount(() => {
  request++;
  observer?.disconnect();
});
</script>

<template>
  <section
    ref="host"
    class="journal-details"
    :aria-label="t('Transaction details')"
    :aria-busy="busy"
  >
    <FrameView
      :scene="scene"
      :style="{ position: 'relative', height: scene.height + 'px' }"
      @event="(action) => (action.type === 'copy' ? copy() : load())"
    />
    <CodeBlock v-if="xml" :code="xml" language="xml" />
  </section>
</template>

<style scoped>
.journal-details {
  min-width: 0;
  max-width: calc(100vw - var(--section-rail-width) - var(--space-md) * 3);
  padding: var(--space-md);
}
.journal-details .code-block {
  max-height: min(600px, 60vh);
  margin-bottom: 0;
}
</style>
