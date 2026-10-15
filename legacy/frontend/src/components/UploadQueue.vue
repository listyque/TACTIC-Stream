<script>
import api from '../api.js';
export default {
 name:'UploadQueue',props:{project:String,target:String,recordKey:String},emits:['changed'],
 data(){return {jobs:[],limits:null,allowed:false,context:'publish',description:'',error:'',status:'',active:'',paused:false,alive:true,controller:null,files:new Map(),actionBusy:false}},
 mounted(){this.load()},beforeUnmount(){this.alive=false;this.paused=true;this.controller?.abort()},
 methods:{
 args(extra={}){return {project:this.project,target:this.target,key:this.recordKey,...extra}},
 bytes(n){return n>=1073741824?(n/1073741824).toFixed(2)+' ГиБ':n>=1048576?(n/1048576).toFixed(1)+' МиБ':n+' байт'},
 stateLabel(s){return ({uploading:'Приём файла',ready:'Готов к check-in',committing:'Выполняется check-in',uncertain:'Проверьте результат в версиях',complete:'Check-in завершён',cancelled:'Отменено'})[s]||s},
 update(job){if(!this.alive)return;const i=this.jobs.findIndex(x=>x.id===job.id);if(i<0)this.jobs.unshift(job);else this.jobs.splice(i,1,job)},
 async load(){this.error='';try{const data=await api.request('/uploads',this.args());if(!this.alive)return;this.jobs=data.items;this.limits=data.limits;this.allowed=data.can_upload}catch(e){if(this.alive)this.error=e.message}},
 async hash(buffer){if(!crypto.subtle)throw Error('SHA-256 требует безопасного контекста: localhost или HTTPS');return new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))},
 hex(bytes){return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')},
 async fingerprint(file){
  const chunk=this.limits.chunk_bytes;const hashes=new Uint8Array(Math.ceil(file.size/chunk)*32);
  for(let offset=0,i=0;offset<file.size;offset+=chunk,i++){
   if(!this.alive||this.paused)throw Error('Проверка файла остановлена');
   this.status='Проверка файла: '+this.bytes(Math.min(file.size,offset+chunk))+' / '+this.bytes(file.size);
   hashes.set(await this.hash(await file.slice(offset,offset+chunk).arrayBuffer()),i*32);
  }
  return this.hex(await this.hash(hashes));
 },
 async pick(event,existing=null){
  const selected=Array.from(event.target.files||[]);event.target.value='';if(!selected.length||this.active||this.actionBusy)return;
  this.error='';this.paused=false;this.active='scan';
  try{
   for(const file of selected){
    if(file.size<1||file.size>this.limits.max_file_bytes)throw Error('Файл вне лимита: '+file.name);
    if(existing&&(file.name!==existing.filename||file.size!==existing.size))throw Error('Выберите исходный файл с тем же именем и размером');
    const fingerprint=await this.fingerprint(file);if(!this.alive)return;
    if(existing&&fingerprint!==existing.fingerprint)throw Error('Содержимое выбранного файла отличается от исходного; продолжение запрещено');
    let job=existing||await api.request('/uploads',this.args({filename:file.name,size:file.size,fingerprint,context:this.context,description:this.description,request_id:crypto.randomUUID()}),'POST');
    this.files.set(job.id,file);this.update(job);await this.send(job,file);
    if(this.paused||!this.alive)break;
   }
  }catch(e){if(this.alive&&e.name!=='AbortError')this.error=e.message}finally{if(this.alive){this.active='';this.status='';this.controller=null}}
 },
 async send(job,file){
  job=await api.request('/upload-status',this.args({upload_id:job.id}));this.update(job);this.active=job.id;
  while(this.alive&&!this.paused&&job.state==='uploading'){
   const part=await file.slice(job.offset,job.offset+job.chunk_bytes).arrayBuffer();
   const sha256=this.hex(await this.hash(part));if(this.paused||!this.alive)break;
   this.controller=new AbortController();
   job=await api.uploadChunk(this.args({upload_id:job.id,offset:job.offset,sha256}),part,this.controller.signal);this.update(job);
  }
 },
 async resume(job){if(!this.files.has(job.id))return;this.active=job.id;this.paused=false;this.error='';try{await this.send(job,this.files.get(job.id))}catch(e){if(this.alive&&e.name!=='AbortError')this.error=e.message}finally{if(this.alive){this.active='';this.controller=null}}},
 pause(){this.paused=true;this.controller?.abort()},
 async finish(job){this.error='';this.actionBusy=true;try{const result=await api.request('/upload-finish',this.args({upload_id:job.id}),'POST');this.update(result);this.files.delete(job.id);if(this.alive)this.$emit('changed')}catch(e){if(this.alive)this.error=e.message;try{this.update(await api.request('/upload-status',this.args({upload_id:job.id})))}catch{}}finally{if(this.alive)this.actionBusy=false}},
 async cancel(job){if(!confirm('Удалить только временную загрузку «'+job.filename+'»?'))return;this.error='';try{this.update(await api.request('/uploads',this.args({upload_id:job.id}),'DELETE'));this.files.delete(job.id)}catch(e){this.error=e.message}},
 async check(job){try{this.update(await api.request('/upload-status',this.args({upload_id:job.id})))}catch(e){this.error=e.message}}
 }
};
</script>
<template>
<section class="upload-queue"><header><h3>Загрузка и check-in</h3><button :disabled="!!active||actionBusy" @click="load">Обновить очередь</button></header>
<p v-if="error" class="error">{{error}}</p>
<template v-if="limits"><p class="muted">До {{bytes(limits.max_file_bytes)}} на файл · части {{bytes(limits.chunk_bytes)}}. После загрузки отдельно выполните check-in.</p>
<div v-if="allowed" class="upload-controls"><label>Context<input v-model="context" :disabled="!!active||actionBusy"></label><label>Описание<textarea v-model="description" rows="2" :disabled="!!active||actionBusy"></textarea></label><label class="button">Выбрать файлы<input class="upload-pick" type="file" multiple :disabled="!!active||actionBusy" @change="pick($event)"></label></div><p v-else class="notice">Загрузка выключена: allow_writes и allow_uploads должны быть включены на тестовой установке.</p>
<p v-if="status" role="status">{{status}}</p><button v-if="active" @click="pause">Приостановить</button>
<article v-for="j in jobs" :key="j.id" class="upload-job" :data-upload-id="j.id"><header><b>{{j.filename}}</b><small>{{stateLabel(j.state)}}</small></header><progress :value="j.offset" :max="j.size"></progress><small>{{bytes(j.offset)}} / {{bytes(j.size)}} · {{j.context}}</small><small v-if="['uploading','ready'].includes(j.state)" class="upload-expiry">Хранится до {{new Date(j.expires*1000).toLocaleString()}}</small>
<p v-if="j.state==='uncertain'" class="error">Check-in мог выполниться до обрыва. Проверьте версии и серверный журнал. Повтор и удаление временного файла автоматически не выполняются.</p>
<code v-if="j.state==='complete'&&j.result?.snapshot" class="receipt">{{j.result.snapshot.code||j.result.snapshot.__search_key__}}</code>
<div class="toolbar"><template v-if="allowed&&j.state==='uploading'"><button v-if="files.has(j.id)" :disabled="!!active||actionBusy" @click="resume(j)">Продолжить</button><label v-else class="button">Выбрать тот же файл<input type="file" :disabled="!!active||actionBusy" @change="pick($event,j)"></label></template><button v-if="j.state==='ready'&&allowed" class="primary" :disabled="!!active||actionBusy" @click="finish(j)">{{actionBusy?'Выполняется…':'Выполнить check-in'}}</button><button v-if="['uploading','ready'].includes(j.state)&&allowed" :disabled="!!active||actionBusy" @click="cancel(j)">Отменить загрузку</button><button v-if="j.state==='committing'" :disabled="actionBusy" @click="check(j)">Проверить состояние</button></div></article>
<p v-if="!jobs.length" class="muted">Очередь пуста.</p><small>Подтверждённая позиция хранится на сервере. После перезахода выберите тот же файл; все его блоки проверяются SHA-256. Это временное хранилище, не новая версия TACTIC.</small></template></section>
</template>
