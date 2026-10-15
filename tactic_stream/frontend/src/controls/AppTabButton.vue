<script setup>
import AppButton from './AppButton.vue'
defineProps({ checked: Boolean })
</script>
<template>
  <AppButton class="app-tab-button" :aria-pressed="checked" />
</template>
<style>
.app-tab-button { border: 0; background: transparent; border-radius: var(--item-radius); font-weight: 400; padding: 0 6px; height: var(--control-height); }
.app-tab-button[aria-pressed="true"] { border: 1px solid var(--primary); color: var(--primary); background: var(--hover); font-weight: 600; }
</style>
