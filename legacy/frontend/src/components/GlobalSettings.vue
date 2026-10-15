<script>
import api from '../api.js';
export default {
 name:'GlobalSettings',props:{project:String,target:String,kind:String},emits:['dirty'],
 data(){return {record:null,changes:{},xml:'',error:'',notice:'',busy:false,seq:0}},
 computed:{dirty(){return Object.keys(this.changes).length>0||Boolean(this.xml)},endpoint(){return this.kind==='license'?'/license':'/system-config'}},
 watch:{dirty(v){this.$emit('dirty',v)},target(){this.load()}},mounted(){this.load()},beforeUnmount(){this.seq++},
 methods:{args(){return {project:this.project,target:this.target}},
 async load(){if(this.dirty&&!confirm('Отменить несохранённые изменения?'))return;const seq=++this.seq;this.busy=true;this.error='';try{const d=await api.request(this.endpoint,this.args());if(seq===this.seq){this.record=d;this.changes={};this.xml=''}}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 value(f){return Object.hasOwn(this.changes,f.name)?this.changes[f.name]:f.value},
 change(f,value){if(value===f.value)delete this.changes[f.name];else this.changes[f.name]=value},
 async choose(e){const file=e.target.files?.[0];if(!file)return;if(file.size>256*1024){this.error='Лицензия должна быть не больше 256 КиБ';return}this.xml=await file.text()},
 async save(){if(!this.record?.can_write||this.busy)return;if(!confirm(this.kind==='license'?'Заменить лицензию после проверки подписи TACTIC?':'Сохранить конфигурацию сервера с резервной копией? После сохранения потребуется ручной перезапуск.'))return;this.busy=true;this.error='';try{const data={...this.args(),revision:this.record.revision};if(this.kind==='license'){data.xml=this.xml;data.confirm='RENEW_LICENSE'}else{data.changes=this.changes;data.confirm='SAVE_SYSTEM_CONFIG'}const r=await api.request(this.endpoint,data,this.kind==='license'?'POST':'PATCH');this.changes={};this.xml='';await this.load();this.notice=r.notice||'Сохранено'}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
</script>
<template>
<section class="global-settings" :aria-label="kind==='license'?'License Manager':'System Configuration'"><header class="widget-toolbar" role="group" aria-label="Действия с настройками"><button @click="load" :disabled="busy">Обновить</button><button class="primary" :disabled="busy||!record?.can_write||!dirty" @click="save">{{busy?'Обработка…':'Сохранить'}}</button></header>
 <p v-if="error" class="error">{{error}}</p><p v-if="notice" class="notice">{{notice}}</p><p v-if="record&&!record.can_write" class="notice">Режим чтения. Для изменения запустите MANAGE_TACTIC.bat configure --writes on на сервере и перезапустите TACTIC.</p>
 <template v-if="record&&kind==='system-config'"><p class="notice">{{record.notice}}</p><div class="global-settings-grid"><fieldset v-for="g in record.groups" :key="g.title"><legend>{{g.title}}</legend><div v-for="f in g.fields" :key="f.name" class="system-field"><label :for="'setting-'+f.name">{{f.label}}<small>{{f.name}}</small></label><select v-if="f.choices.length" :id="'setting-'+f.name" :disabled="!record.can_write" :value="value(f)" @change="change(f,$event.target.value)"><option v-for="o in f.choices" :value="o" :key="o">{{o}}</option></select><select v-else-if="f.kind==='boolean'" :id="'setting-'+f.name" :disabled="!record.can_write" :value="value(f)" @change="change(f,$event.target.value)"><option value="">По умолчанию</option><option value="true">true</option><option value="false">false</option></select><input v-else :id="'setting-'+f.name" :disabled="!record.can_write" :type="f.secret?'password':f.kind==='integer'?'number':'text'" :autocomplete="f.secret?'new-password':undefined" :value="value(f)" :placeholder="f.secret&&f.configured?'Настроено; пустое поле не меняет секрет':''" @input="change(f,$event.target.value)"></div></fieldset></div></template>
 <template v-if="record&&kind==='license'"><p v-if="record.message" class="warning-text">{{record.message}}</p><dl class="license-info"><template v-for="(v,k) in record.info" :key="k"><dt>{{k}}</dt><dd>{{v===null||v===''?'—':v}}</dd></template><dt>Проверка TACTIC</dt><dd>{{record.licensed?'Лицензия подтверждена':'Нет подтверждённой лицензии'}}</dd></dl><fieldset><legend>Renew License</legend><p>Проверка подписи выполняется исходным License. Только после неё RenewLicenseCbk заменяет файл.</p><input type="file" accept=".xml,text/xml,application/xml" :disabled="!record.can_write||busy" @change="choose"><p v-if="xml">Файл выбран: {{xml.length}} символов. Содержимое не выполняется и не выводится как HTML.</p></fieldset></template>
</section>
</template>
