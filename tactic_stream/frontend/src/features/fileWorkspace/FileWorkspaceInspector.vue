<script>
import { t } from '../../i18n.js'
import AppTabButton from '../../controls/AppTabButton.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { prettySize } from '../checkin/files.js'

export default {
  components:{AppTabButton,AppTextArea,AppIcon},
  props:{call:Function,row:Object,workspace:String,stream:String,scope:String,shelved:Boolean},
  data(){return {tab:'details',info:null,busy:false,error:'',generation:0,aborter:null,timer:null}},
  computed:{key(){return JSON.stringify([this.row?.source_path || this.row?.path,this.row?.stream || this.stream,this.scope,this.workspace,this.tab])},
    fields(){const info=this.info,file=info?.file;if(!info)return [];
      return [['Workspace location',info.local_path || '—'],['Depot location','//'+info.stream+'/'+info.path],
        ['Revision','#'+(file?.number || '—')+' · Have #'+(info.have?.number || '—')+' · Head #'+(info.head?.number || '—')],
        ['Submitted at',info.submitted_at ? new Date(info.submitted_at/1000).toLocaleString() : '—'],
        ['File size',prettySize(file?.size || 0)],['Author',info.author || '—'],['Changelist',info.change_number?'#'+info.change_number:'—'],
        ['Description',info.description || '—'],['Integration source',info.provenance ? info.provenance.stream+' · '+info.provenance.change+' · '+info.provenance.version : '—'],['SHA-256',file?.sha256 || '—']]}
  },
  watch:{key:{immediate:true,handler(){clearTimeout(this.timer);this.aborter?.abort();this.generation++;this.info=null;this.error='';this.busy=!!this.row?.path;if(this.busy)this.timer=setTimeout(()=>this.load(),120)}}},
  beforeUnmount(){clearTimeout(this.timer);this.generation++;this.aborter?.abort()},
  methods:{t,prettySize,
    async load(){const generation=this.generation;this.aborter=new AbortController();const signal=this.aborter.signal;
      const options={stream:this.row.stream || this.stream,path:this.row.source_path || this.row.path};
      if(this.scope)options[this.shelved?'shelf':'change']=this.scope;
      try {const info=await this.call('file_info',{...options,...(this.workspace?{workspace:this.workspace}:{}),preview:this.tab==='preview'},signal);
        if(generation===this.generation)this.info=info
      }catch(error){if(generation===this.generation&&error.name!=='AbortError')this.error=error.message}
      finally{if(generation===this.generation)this.busy=false}
    }
  }
}
</script>

<template>
  <section class="file-workspace-inspector" :aria-label="t('File details')">
    <header role="tablist" :aria-label="t('File details')">
      <AppTabButton v-for="item in [{id:'details',title:'Details'},{id:'checkout',title:'Checked Out By'},{id:'preview',title:'Preview'}]" :key="item.id" :label="item.title" :checked="tab===item.id" @click="tab=item.id" />
      <span v-if="busy" role="status">{{ t('Loading') }}</span>
    </header>
    <div class="file-workspace-inspector-body">
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <p v-else-if="!info&&!busy" class="muted">{{ t('Select a file to inspect') }}</p>
      <dl v-if="info&&tab==='details'"><template v-for="[title,value] in fields" :key="title"><dt>{{ t(title) }}</dt><dd>{{ value }}</dd></template></dl>
      <template v-if="info&&tab==='checkout'">
        <p v-if="!info.holders.length" class="muted">{{ t('No active checkout') }}</p>
        <p v-for="holder in info.holders" :key="holder.change"><AppIcon :name="holder.mode==='exclusive'?'lock':'edit'" /> {{ holder.owner }} · {{ holder.workspace }} · #{{ holder.number || holder.change }} · {{ t(holder.mode==='exclusive'?'Exclusive checkout':'Ordinary checkout') }}</p>
      </template>
      <template v-if="info&&tab==='preview'">
        <p v-if="!info.preview" class="muted">{{ t('No content available for this file') }}</p>
        <template v-else>
          <p v-if="info.preview.kind==='binary'" class="muted">{{ t('Binary file') }} · {{ prettySize(info.preview.size) }} · {{ info.preview.sha256 }}</p>
          <p v-if="info.preview.truncated" class="muted">{{ t('Preview shows the first 256 KiB') }}</p>
          <img v-if="info.preview.kind==='image'" :src="info.preview.image" :alt="info.path" />
          <AppTextArea v-else :model-value="info.preview.text" readonly label="File preview" />
        </template>
      </template>
    </div>
  </section>
</template>

<style scoped>
.file-workspace-inspector{display:flex;flex-direction:column;min-height:140px;max-height:300px;flex:0 0 220px;border-top:1px solid var(--outline-variant);overflow:hidden}
.file-workspace-inspector header{display:flex;align-items:center;gap:4px;flex-shrink:0}
.file-workspace-inspector-body{overflow:auto;scrollbar-gutter:stable;min-height:0;padding:8px}
dl{display:grid;grid-template-columns:minmax(90px,145px) minmax(0,1fr);gap:6px 12px;margin:0}
dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap;user-select:text}
img{display:block;max-width:100%;max-height:220px;object-fit:contain}
</style>
