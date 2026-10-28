<script setup>
import { ref, onMounted } from 'vue';
import AppButton from '../../frontend/src/controls/AppButton.vue';
const configuration = ref(null);
const a = ref(null),
  b = ref(null),
  owner = ref(null),
  child = ref(null);
const clicks = ref(0);
const headerPresent = ref(true);
onMounted(() => {
  window.host = {
    a: a.value,
    configuration: configuration.value,
    setHeader: value => headerPresent.value = value,
    b: b.value,
    owner: owner.value,
    child: child.value
  };
});
</script>
<template>
  <button id="outside" @click="a.show()">Open</button>
  <dialog
    ref="a"
    id="a"
    v-window="{ kind: 'help', type: 'window' }"
    style="margin: 0; left: 20px; top: 40px; width: 380px; height: 240px"
  >
    <header v-if="headerPresent">
      <strong>A</strong><AppButton label="Close A" @click="a.close()" />
    </header>
    <AppButton id="action" label="Action" @click="clicks++" />
    <input aria-label="Draft" /><output>{{ clicks }}</output>
  </dialog>
  <dialog
    ref="b"
    id="b"
    v-window="{ kind: 'help', type: 'window' }"
    style="margin: 0; left: 600px; top: 350px; width: 380px; height: 240px"
  >
    <header>
      <strong>B</strong><AppButton label="Close B" @click="b.close()" />
    </header>
  </dialog>
  <dialog ref="configuration" id="configuration" class="configuration-dialog"
    v-window="{kind:'configuration', type:'window'}">
    <header v-if="headerPresent"><strong>Configuration</strong><AppButton label="Close configuration" @click="configuration.close()" /></header>
  </dialog>
  <dialog ref="owner" id="owner">
    <button id="launcher" @click="child.show()">Open child</button>
  </dialog>
  <dialog ref="child" id="child" v-window="{ kind: 'help', type: 'window' }">
    <header>
      Child<AppButton label="Close child" @click="child.close()" />
    </header>
    <input aria-label="Child text" />
  </dialog>
</template>
<style scoped>
header {
  display: flex;
  height: 40px;
  align-items: center;
}
header > strong {
  flex: 1;
}
</style>
