<script>
export default {
 name:'MessageContent',props:{content:Object},
 methods:{show(value){return typeof value==='object'?JSON.stringify(value,null,2):String(value??'—')}}
};
</script>
<template>
<div class="message-content" v-if="content"><p class="message-text">{{content.text}}</p><template v-if="content.progress!==null&&content.progress!==undefined"><progress :value="content.progress" max="100"></progress><small>{{content.progress}}%</small></template><small v-if="content.object"><code>{{content.object.search_type}} · {{content.object.code}}</code></small><dl v-if="content.changes?.length" class="message-changes"><template v-for="change in content.changes" :key="change.field"><dt>{{change.field}}</dt><dd>{{show(change.value)}}</dd></template></dl></div>
</template>
