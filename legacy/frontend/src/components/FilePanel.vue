<script>
import api from '../api.js';
import UploadQueue from './UploadQueue.vue';
export default {
 name:'FilePanel',components:{UploadQueue},props:{project:String,target:String,recordKey:String},emits:['changed'],
 data(){return {page:{items:[],total:0,offset:0,limit:40},context:'',archives:false,error:'',busy:false,preview:null,currentChoice:null,seq:0,alive:true,uploadsOpen:false}},
 mounted(){this.load()},beforeUnmount(){this.alive=false;this.seq++},
 methods:{
 args(extra={}){return {project:this.project,target:this.target,key:this.recordKey,...extra}},
 async load(offset=0){const seq=++this.seq;this.busy=true;this.error='';try{const page=await api.request('/file-versions',this.args({offset,limit:40,context:this.context,record_state:this.archives?'all':'active'}));if(seq===this.seq&&this.alive)this.page=page}catch(e){if(seq===this.seq&&this.alive)this.error=e.message}finally{if(seq===this.seq&&this.alive)this.busy=false}},
 url(s,f,preview=false){const url=new URL('/api/ui/v2/file',location.origin);Object.entries(this.args({snapshot:s.key,file:f.code,preview:preview?'1':'0'})).forEach(([k,v])=>url.searchParams.set(k,v));return url.href},
 async choose(snapshot){this.error='';try{this.currentChoice=await api.request('/snapshot-current',this.args({snapshot:snapshot.key}))}catch(e){this.error=e.message}},
 async setCurrent(){this.busy=true;this.error='';try{await api.request('/snapshot-current',this.args({snapshot:this.currentChoice.selected.key,revision:this.currentChoice.revision,confirm:'SET_CURRENT'}),'POST');this.currentChoice=null;await this.load(this.page.offset);this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 checked(){this.load();this.$emit('changed')},
 truth(v){return v===true||v===1||v==='true'||v==='t'},
 }
};
</script>
<template>
<section class="file-panel"><div class="toolbar"><h3>Версии и файлы</h3><span class="spacer"></span><button :class="{primary:uploadsOpen}" @click="uploadsOpen=!uploadsOpen">Загрузка файлов</button></div>
<UploadQueue v-if="uploadsOpen" :project="project" :target="target" :record-key="recordKey" @changed="checked"/>
<form class="version-filter toolbar" @submit.prevent="load()"><input v-model="context" placeholder="Точный context или все" aria-label="Контекст версий"><label><input type="checkbox" v-model="archives" @change="load()">Включая архив</label><button :disabled="busy">Применить</button></form><p v-if="error" class="error">{{error}}</p><p class="notice">{{page.notice}}</p>
<article v-for="s in page.items" :key="s.key" class="snapshot"><header><b>{{s.context}} · v{{s.version}}</b><span v-if="truth(s.is_current)" class="tag">current</span><span v-if="truth(s.is_latest)" class="tag">latest</span><span v-if="s.s_status==='retired'" class="tag">архив</span></header><small>{{s.timestamp}} · {{s.login}} · {{s.code}}</small><p>{{s.description}}</p>
<div v-for="f in s.files" :key="f.code" class="file-row"><template v-if="!f.missing_registration"><a :href="url(s,f)" download>{{f.name}}</a><small>{{f.type}} · {{f.size??'—'}} байт</small><button v-if="f.preview" @click="preview={url:url(s,f,true),mime:f.mime,name:f.name}">Просмотр</button></template><p v-else class="error">{{f.code}}: запись файла отсутствует; содержимое не подменяется.</p></div><button v-if="Number(s.version)>=0&&s.s_status!=='retired'&&!truth(s.is_current)" @click="choose(s)">Выбрать current…</button></article>
<p v-if="!busy&&!page.items.length" class="muted">Версии не найдены.</p><footer class="toolbar"><small>{{page.total? page.offset+1:0}}–{{page.offset+page.items.length}} из {{page.total}}</small><span class="spacer"></span><button :disabled="busy||!page.offset" @click="load(Math.max(0,page.offset-page.limit))">Назад</button><button :disabled="busy||!page.has_more" @click="load(page.offset+page.limit)">Далее</button></footer>
<Teleport to="body"><div v-if="currentChoice" class="modal-backdrop"><section class="modal current-dialog" role="dialog"><header><h3>Сменить current-версию</h3><button @click="currentChoice=null">×</button></header><p>{{currentChoice.selected.context}} · v{{currentChoice.selected.version}} · {{currentChoice.selected.code}}</p><p>Сейчас current: {{currentChoice.current.map(s=>s.code).join(', ')||'не выбрана'}}</p><p class="notice">{{currentChoice.notice}}</p><p v-if="error" class="error">{{error}}</p><button class="primary" :disabled="busy||!currentChoice.can_write" @click="setCurrent">Подтвердить current</button></section></div>
<div v-if="preview" class="modal-backdrop" @click.self="preview=null"><section class="modal preview-modal"><header><h3>{{preview.name}}</h3><button @click="preview=null">×</button></header><img v-if="preview.mime.startsWith('image/')" :src="preview.url" :alt="preview.name"><video v-else-if="preview.mime.startsWith('video/')" :src="preview.url" controls></video><audio v-else :src="preview.url" controls></audio></section></div></Teleport></section>
</template>
