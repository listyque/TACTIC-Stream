<script setup>
import CodeBlock from '../../controls/CodeBlock.vue'
import { t } from '../../i18n.js'
defineProps({ cell: Object, height: Number })
</script>

<template>
  <div class="table-structured" :style="{ maxHeight: (height || (cell?.language === 'xml' ? 600 : 300)) + 'px' }">
    <span v-if="cell?.diagnostic" role="status" class="error-text">{{ t('XML Parse Error') }}: {{ cell.diagnostic }}</span>
    <CodeBlock :code="cell?.text || ''" language="text" />
  </div>
</template>

<style scoped>
.table-structured { overflow:auto; min-width:0; }
.table-structured :deep(.code-block) { background:transparent; padding:0; margin:0; border:0; border-radius:0; white-space:pre; overflow:visible; font-family:Consolas,monospace; font-size:var(--text-body); line-height:normal; }
</style>
