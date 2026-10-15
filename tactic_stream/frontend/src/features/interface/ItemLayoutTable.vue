<script setup>
import { computed } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import ItemLayout from './ItemLayout.vue'

const props=defineProps({layout:Object,nodes:Array,readOnly:Boolean,editing:Boolean,selectedElement:String})
const emit=defineEmits(['activate','context','action','completion','element'])
const columns=computed(()=>props.layout.elements.filter(item=>!item.parent && !item.hidden && ['all','main'].includes(item.variant)))
</script>
<template>
  <div class="item-layout-table-scroll">
    <table class="item-layout-table"><thead><tr>
      <th v-for="column in columns" :key="column.name"><AppButton v-if="editing" :label="column.title" :translate-label="false" :highlighted="selectedElement===column.name" @click="emit('element',column.name)" /><template v-else>{{ column.title }}</template></th>
      <th v-if="$slots.actions">{{ t('Actions') }}</th>
    </tr></thead><tbody><tr v-for="node in nodes" :key="node.id || node.record?.__search_key__" @click="emit('activate',node,$event)" @contextmenu.prevent="emit('context',node,$event)">
      <td v-for="column in columns" :key="column.name"><ItemLayout :layout="layout" :node="node" :only="column.name" :read-only="readOnly" :editing="editing" :selected-element="selectedElement" @action="(owner,action,event)=>emit('action',owner,action,event)" @completion="(owner,item)=>emit('completion',owner,item)" @element="emit('element',$event)" /></td>
      <td v-if="$slots.actions"><slot name="actions" :node="node" /></td>
    </tr></tbody></table>
  </div>
</template>
<style>
.item-layout-table-scroll { overflow:auto;max-width:100%; }
.item-layout-table { width:100%; }
.item-layout-table th,.item-layout-table td { padding:8px;text-align:left; }
.item-layout-table td > .item-layout { display:block; }
</style>
