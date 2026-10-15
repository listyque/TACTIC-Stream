<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppTextField from '../../controls/AppTextField.vue'
import ItemSurface from '../../controls/ItemSurface.vue'
import AppSplitter from '../../controls/AppSplitter.vue'
defineProps({ rows:Array, selected:Object, draft:Object, repositories:Array, busy:Boolean, administrator:Boolean, after:String })
const emit=defineEmits(['select','edit','change','save','reset','cancel','refresh','more'])
const host=ref(null), narrow=ref(false), desktopSplit=ref(55), mobileSplit=ref(40)
const split=computed({get:()=>narrow.value?mobileSplit.value:desktopSplit.value,set:value=>{if(narrow.value)mobileSplit.value=value;else desktopSplit.value=value}})
const observer=new ResizeObserver(entries=>{narrow.value=(entries[0].borderBoxSize?.[0]?.inlineSize||entries[0].contentRect.width)<600})
onMounted(()=>observer.observe(host.value))
onBeforeUnmount(()=>observer.disconnect())
</script>
<template>
  <section ref="host" class="depots-catalog" :class="{narrow}" :aria-label="t('Depots')">
    <header class="depot-actions"><h3>{{ t('Depots') }}</h3><AppButton label="Refresh" icon="refresh" :disabled="busy" @click="emit('refresh')" /><AppButton v-if="after" label="Next page" icon="next" :disabled="busy" @click="emit('more')" /></header>
    <div class="depot-content">
    <aside :style="{flexBasis:`max(0px,calc(${split}% - 10px))`}"><ItemSurface v-for="row in rows" :key="row.code" :selected="selected?.code===row.code" normal-color="transparent" selected-color="var(--selected)" :rail-visible="selected?.code===row.code" :separator-visible="false"><AppButton class="depot-row" :label="row.code" :translate-label="false" icon="database" :aria-pressed="selected?.code===row.code" @click="emit('select',row)"><span class="depot-row-text"><strong>{{ row.code }}</strong><small>{{ row.title }} · {{ row.storage?.repository || t('Project storage') }}</small></span></AppButton></ItemSurface><p v-if="!rows.length">{{ t('No permitted records on this page') }}</p></aside>
    <AppSplitter v-model="split" label="Depots" :horizontal="narrow" :proportional="true" :min="0" :max="100" />
    <div class="depot-detail">
      <form v-if="draft" @submit.prevent="emit('save')">
        <h3>{{ t(draft.creating?'New depot':'Edit depot') }}</h3>
        <label><span>{{ t('Depot code') }}</span><AppTextField :model-value="draft.code" label="Depot code" :readonly="!draft.creating" :disabled="busy" @update:model-value="emit('change',{...draft,code:$event})" /></label>
        <label><span>{{ t('Name') }}</span><AppTextField :model-value="draft.title" label="Name" :disabled="busy" @update:model-value="emit('change',{...draft,title:$event})" /></label>
        <label><span>{{ t('Repository') }}</span><AppSelect :model-value="draft.repository" label="Repository" :options="[{value:'',label:t('Project storage')},...repositories.map(value=>({value,label:value}))]" :translate-labels="false" :disabled="busy" @update:model-value="emit('change',{...draft,repository:$event})" /></label>
        <p>{{ t('Repository changes apply to new uploads. Existing file contents stay in their original storage.') }}</p>
        <p>{{ t('Depot paths are case-sensitive. Access is configured in Administration → Rules using file_depot.') }}</p>
        <div class="depot-actions"><AppButton label="Reset" icon="undo" :disabled="busy" @click="emit('reset')" /><AppButton label="Cancel" icon="close" :disabled="busy" @click="emit('cancel')" /><AppButton :label="draft.creating?'Create':'Save'" icon="save" type="submit" :disabled="busy||!draft.code.trim()" /></div>
      </form>
      <template v-else><h3>{{ selected?.code || t('Select a depot') }}</h3><p v-if="selected?.code">{{ selected.title }}<br>{{ t('Repository') }}: {{ selected.storage?.repository || t('Project storage') }}<br>{{ t('Revision') }}: {{ selected.revision }}<br>{{ t('Case-sensitive depot paths') }}</p><div v-if="administrator" class="depot-actions"><AppButton label="New depot" icon="add" :disabled="busy" @click="emit('edit',null)" /><AppButton label="Edit depot" icon="edit" :disabled="busy||!selected?.code" @click="emit('edit',selected)" /></div></template>
    </div>
    </div>
  </section>
</template>
<style scoped>
.depots-catalog{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden;gap:8px;padding:7px;border:1px solid var(--outline-variant);border-radius:var(--surface-radius);background:var(--surface-deep)}.depot-content{display:flex;flex:1;min-height:0;min-width:0}.depots-catalog h3{font-size:var(--text-title);margin:0}.depots-catalog header h3{flex:1}.depots-catalog aside{flex:0 0 auto;min-width:0;min-height:0;overflow:auto}.depot-detail{flex:1;min-width:0;overflow:auto}.depot-row{width:100%;text-align:left;justify-content:flex-start;padding:12px;gap:10px;border:0;background:transparent}.depot-row:hover:not(:disabled){background:transparent;border-color:transparent}.depot-row :deep(.app-icon){color:var(--primary);font-size:19px;width:19px;height:19px}.depot-row-text{display:flex;flex-direction:column;gap:4px;min-width:0}.depot-row small{font-size:var(--text-label)}.depot-row small,.depot-detail label>span,.depot-detail p{color:var(--muted);overflow-wrap:anywhere}.depot-detail form,.depot-detail label{display:flex;flex-direction:column;gap:8px}.depot-detail h3,.depot-detail p{margin:0}.depot-detail h3{font-size:var(--text-title);line-height:20px}.depot-detail{display:flex;flex-direction:column;gap:8px}.depot-actions{display:flex;flex-wrap:wrap;gap:8px}.depots-catalog.narrow .depot-content{flex-direction:column}
</style>
