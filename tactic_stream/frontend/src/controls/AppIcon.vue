<script setup>
import { computed } from 'vue';
import { appearance } from '../appearance.js';
import { resolveIcon } from '../icons.js';
import '../icons.css';

const props = defineProps({ name: String });
const icon = computed(() => resolveIcon(props.name, appearance.iconSet));
</script>

<template>
  <span
    v-if="icon"
    class="app-icon"
    :class="'icon-' + icon[0]"
    :data-icon="name"
    aria-hidden="true"
    ><span class="icon-glyph">{{ icon[1] }}</span></span
  >
</template>
