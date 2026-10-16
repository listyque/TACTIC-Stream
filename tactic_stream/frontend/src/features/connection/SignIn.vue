<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/connection/sign_in.ui.mjs';
const props = defineProps({
  login: String,
  password: String,
  busy: Boolean,
  ready: Boolean,
  error: String,
  version: String
});
const emit = defineEmits(['update:login', 'update:password', 'submit', 'help']);
const body = ref(null),
  viewport = ref({ width: 440, height: 376 });
const model = computed(() => ({
  ...props,
  product: 'TACTIC Stream',
  server: location.host,
  nativeTicket: false,
  cancelable: false,
  canHelp: true
}));
const scene = computed(() =>
  UI.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(body.value);
});
onBeforeUnmount(() => observer?.disconnect());
function dispatch(action) {
  if (action.type === 'login' || action.type === 'password')
    emit('update:' + action.type, action.value);
  else if (action.type === 'help') emit('help', 'getting_started');
  else if (action.type === 'submit' && UI.canSubmit(model.value))
    emit('submit');
}
</script>
<template>
  <section class="sign-in">
    <div class="sign-in-appearance"><slot /></div>
    <form
      ref="body"
      class="sign-in-frame"
      @submit.prevent="dispatch({ type: 'submit' })"
    >
      <FrameView :scene="scene" @event="dispatch" />
    </form>
  </section>
</template>
<style scoped>
.sign-in {
  width: min(440px, 100dvw);
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.sign-in-appearance {
  display: flex;
  justify-content: flex-end;
  padding-inline: 18px;
}
.sign-in-frame {
  height: min(470px, calc(100dvh - 64px));
  min-height: 300px;
  position: relative;
  margin: 0;
  display: block;
}
</style>
