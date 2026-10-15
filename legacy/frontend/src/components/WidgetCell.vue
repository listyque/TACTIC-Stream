<script>
export default {
 name:'WidgetCell',props:{row:Object,field:Object,fallback:String},emits:['open'],
 computed:{
  cell(){return this.row?.cells?.[this.field.name]},
  text(){return this.cell?this.cell.text:this.fallback},
  initials(){return String(this.cell?.empty?'':this.text||'').trim().split(/\s+/).slice(0,2).map(s=>s[0]||'').join('').toUpperCase()},
  css(){return {'cell-error':this.cell?.kind==='error','cell-negative':this.cell?.negative,'cell-single-line':this.field.single_line}},
  safeColor(){const value=String(this.cell?.color||'');return /^(#[0-9a-f]{3,8}|[a-z]+|(?:rgb|rgba|hsl|hsla)\([0-9.,% +\-]+\))$/i.test(value)?value:undefined}
 }
};
</script>
<template>
<span class="widget-cell-value" :class="css">
 <span v-if="cell?.kind==='thumbnail'" class="thumbnail-cell" :class="'thumbnail-'+cell.state" :style="{'--thumb-size':cell.size+'px'}"><button v-if="cell.image && cell.detail!=='false' && cell.detail!=='none'" class="thumb-open" @click.stop="$emit('open',{record_detail:true})" :title="cell.text"><img :src="cell.image" :alt="cell.text" loading="lazy"></button><img v-else-if="cell.image && cell.detail==='none'" :src="cell.image" :alt="cell.text" loading="lazy"><a v-else-if="cell.image" :href="cell.href" target="_blank" rel="noopener noreferrer" @click.stop :title="cell.text"><img :src="cell.image" :alt="cell.text" loading="lazy"></a><span v-else class="thumbnail-placeholder" :title="cell.text">{{cell.state==='file'?'▤':cell.state==='error'||cell.state==='missing'?'!':'▧'}}</span><small v-if="cell.show_filename||cell.state==='file'">{{cell.text}}</small></span>
 <span v-else-if="cell?.kind==='project-database'" class="project-db-cell"><span :class="cell.exists?'ok':'cell-error'">Exists: {{cell.exists?'Yes':'No'}}</span><span :class="cell.current?'ok':'warning'">Version: {{cell.version||'—'}}</span></span>
 <span v-else-if="cell?.kind==='status'" class="status-chip" :class="{empty:cell.empty}" :style="{'--status-color':safeColor}"><span class="status-dot"></span>{{cell.text}}</span>
 <span v-else-if="cell?.kind==='login'" class="login-cell" :class="{empty:cell.empty}" :title="cell.login"><span v-if="!cell.empty" class="avatar-initials">{{initials}}</span><span>{{cell.text}}</span></span>
 <span v-else-if="cell?.kind==='color'" class="color-cell"><span class="color-swatch" :style="{background:safeColor}"></span><code>{{cell.text||'—'}}</code></span>
 <input v-else-if="cell?.kind==='boolean'" class="display-checkbox" type="checkbox" :checked="cell.checked" disabled :aria-label="cell.text">
 <button v-else-if="cell?.kind==='widget'" class="text-button widget-cell-link" @click.stop="$emit('open',cell)">{{cell.text}}</button>
 <details v-else-if="cell?.kind==='xml'"><summary>XML</summary><pre class="xml-cell">{{cell.text}}</pre></details>
 <a v-else-if="cell?.kind==='link'" :href="cell.href" :target="cell.external?'_blank':undefined" rel="noopener noreferrer" @click.stop :title="cell.text">↗ {{cell.text}}</a>
 <span v-else>{{text}}</span>
</span>
</template>
