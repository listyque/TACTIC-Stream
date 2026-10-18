<script setup>
import { computed, ref, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import UserPicker from '../../controls/UserPicker.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/forms.ui.mjs';
const props = defineProps({
  mode: String,
  text: String,
  users: Array,
  recipients: Array,
  login: String,
  busy: Boolean,
  valid: Boolean,
  canCreateGroup: Boolean,
  activeSearch: Boolean
});
const emit = defineEmits([
  'update:text',
  'update:recipients',
  'submit',
  'cancel',
  'clear-search'
]);
const root = ref(null),
  width = ref(408),
  height = ref(508),
  descriptionHeight = ref(72);
let observer;
const people = computed(() => ['create', 'members'].includes(props.mode));
const scene = computed(() =>
  UI.form(
    { ...props, count: props.recipients?.length || 0 },
    width.value,
    height.value,
    appearance.language,
    { description: descriptionHeight.value }
  )
);
const peoplePort = {
  setup(_, { attrs }) {
    return () =>
      h(UserPicker, {
        ...attrs,
        users: props.users,
        currentLogin: props.login,
        disabled: props.busy,
        modelValue: props.recipients,
        'onUpdate:modelValue': (value) => emit('update:recipients', value)
      });
  }
};
const descriptionPort = {
  setup(_, { attrs }) {
    const text = ref(null);
    let resize;
    onMounted(() => {
      resize = observeFrameSizes(() => {
        const value = text.value.getBoundingClientRect().height;
        if (value > 0) descriptionHeight.value = value;
      });
      resize.observe(text.value);
    });
    onBeforeUnmount(() => resize?.disconnect());
    return () =>
      h('div', attrs, [
        h(
          'p',
          {
            ref: text,
            style: { margin: 0, fontSize: '13px', lineHeight: '17px' }
          },
          UI.description(props.mode, appearance.language)
        )
      ]);
  }
};
function action(event) {
  if (event.type === 'text') emit('update:text', event.value);
  else emit(event.type);
}
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const size = entries[0].contentRect;
    if (size.width > 0) {
      width.value = size.width;
      if (people.value) height.value = size.height;
    }
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="root"
    class="messages-form-surface"
    :class="{ people }"
    :style="people ? {} : { height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      :views="{
        people: { component: peoplePort },
        description: { component: descriptionPort }
      }"
      @event="action"
    />
  </div>
</template>
<style>
.messages-form-surface {
  position: relative;
  flex: none;
  min-width: 0;
}
.messages-form-surface.people {
  flex: 1;
  min-height: 0;
}
.messages-form-surface > .frame-view {
  height: 100%;
}
</style>
