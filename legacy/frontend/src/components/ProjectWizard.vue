<script>
import api from '../api.js';
export default {
 name:'ProjectWizard',props:{project:String,target:String},emits:['changed','dirty'],
 data(){return {step:0,busy:false,error:'',options:null,code:'',title:'',description:'',type:'default',review:null,result:null,jump:true,submitted:false}},
 async mounted(){try{this.options=await api.request('/project-create',{project:this.project,target:this.target})}catch(e){this.error=e.message}},
 computed:{summaryType(){return this.options?.types?.find(t=>t.code===this.type)?.title||this.type},validDetails(){return /^[a-z][a-z0-9_]{0,29}$/.test(this.code)&&this.title.trim().length>0&&this.title.length<=200}},
 watch:{code(){this.modified()},title(){this.modified()},description(){this.modified()},type(){this.modified()}},
 methods:{
  modified(){this.review=null;this.$emit('dirty',!this.result&&Boolean(this.code||this.title||this.description))},
  payload(){return {project:this.project,target:this.target,code:this.code,title:this.title,type:this.type,description:this.description}},
  async next(){if(this.busy)return;this.error='';if(this.step===0){if(!this.validDetails){this.error='Укажите название и код: до 30 строчных латинских букв, цифр или _, начиная с буквы.';return}this.step=1;return}
   this.busy=true;try{this.review=await api.request('/project-preflight',this.payload(),'POST');this.step=2}catch(e){this.error=e.message}finally{this.busy=false}},
  back(){if(this.busy||this.submitted)return;this.error='';this.step=Math.max(0,this.step-1);this.review=null},
  async create(){if(this.busy||!this.review||this.submitted)return;this.busy=true;this.error='';this.submitted=true;
   try{this.result=await api.request('/project-create',{...this.payload(),revision:this.review.revision},'POST');this.step=3;this.$emit('dirty',false);this.$emit('changed',{...this.result,open:this.jump})}
   catch(e){this.error=e.message;if(e.status&&e.status<500)this.submitted=false;else this.error+=' Перед повторной попыткой проверьте список проектов: ответ команды мог быть потерян.'}
   finally{this.busy=false}},
  openProject(){this.$emit('changed',{...this.result,open:true})}
 }
};
</script>
<template>
<section class="project-wizard" aria-label="Мастер создания проекта TACTIC" :aria-busy="busy">
 <ol class="wizard-steps" aria-label="Этапы"><li v-for="(label,i) in ['Проект','Схема','Проверка','Готово']" :key="label" :class="{current:step===i,complete:step>i}" :aria-current="step===i?'step':undefined"><span>{{step>i?'✓':i+1}}</span>{{label}}</li></ol>
 <p v-if="error" class="error" role="alert">{{error}}</p>
 <p v-if="options&&!options.can_write" class="notice">Создание выключено настройкой записи native UI. Включите запись для своей тестовой установки.</p>
 <form v-if="step<3" @submit.prevent="step===2?create():next()">
  <fieldset :disabled="busy||submitted" class="wizard-fields">
   <div v-if="step===0" class="wizard-details"><label>Название<input v-model="title" maxlength="200" placeholder="Название проекта" autocomplete="off" required></label><label>Код проекта<input v-model="code" maxlength="30" pattern="[a-z][a-z0-9_]{0,29}" placeholder="my_project" autocomplete="off" required><small>Используется в имени базы и адресе. После создания не переименовывается этим мастером.</small></label><label>Описание<textarea v-model="description" rows="4" maxlength="10000" placeholder="Назначение проекта"></textarea></label></div>
   <div v-else-if="step===1" class="wizard-sources"><label v-for="t in options?.types" :key="t.code" class="wizard-source" :class="{selected:type===t.code}"><input type="radio" v-model="type" :value="t.code" name="project-type"><strong>{{t.title}}</strong><p>{{t.description}}</p></label><p class="muted" v-for="note in options?.unsupported" :key="note">{{note}}</p></div>
   <div v-else class="wizard-review"><dl><dt>Название</dt><dd>{{review?.summary.title}}</dd><dt>Код / база</dt><dd><code>{{code}}</code></dd><dt>Исходная схема</dt><dd>{{summaryType}}</dd><dt>Описание</dt><dd>{{description||'—'}}</dd></dl><p class="notice">{{review?.notice}}</p><label class="inline-label"><input type="checkbox" v-model="jump">Перейти в новый проект после создания</label></div>
  </fieldset>
  <footer class="wizard-actions"><button type="button" v-if="step>0" :disabled="busy||submitted" @click="back">Назад</button><span class="spacer"></span><span v-if="busy" role="status">{{step===2?'Создание базы и выполнение исходных команд…':'Проверка…'}}</span><button class="primary" :disabled="busy||submitted||!options?.can_write||step===0&&!validDetails">{{step===2?'Создать проект':step===1?'Проверить':'Далее'}}</button></footer>
 </form>
 <div v-else class="wizard-success"><h3>Проект «{{result.title}}» создан</h3><p>{{result.notice}}</p><button class="primary" @click="openProject">Открыть проект →</button><p><code>{{result.project_url}}</code></p></div>
</section>
</template>
