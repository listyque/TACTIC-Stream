<script>
import { t } from '../../i18n.js';
import WorkspaceInspectorView from './inspection/WorkspaceInspectorView.vue';

export default {
  components: { WorkspaceInspectorView },
  props: {
    call: Function,
    row: Object,
    workspace: String,
    stream: String,
    scope: String,
    shelved: Boolean
  },
  data() {
    return {
      tab: 'details',
      info: null,
      busy: false,
      error: '',
      generation: 0,
      aborter: null,
      timer: null
    };
  },
  computed: {
    key() {
      return JSON.stringify([
        this.row?.source_path || this.row?.path,
        this.row?.stream || this.stream,
        this.scope,
        this.workspace,
        this.tab
      ]);
    }
  },
  watch: {
    key: {
      immediate: true,
      handler() {
        clearTimeout(this.timer);
        this.aborter?.abort();
        this.generation++;
        this.info = null;
        this.error = '';
        this.busy = !!this.row?.path;
        if (this.busy) this.timer = setTimeout(() => this.load(), 120);
      }
    }
  },
  beforeUnmount() {
    clearTimeout(this.timer);
    this.generation++;
    this.aborter?.abort();
  },
  methods: {
    t,
    async load() {
      const generation = this.generation;
      this.aborter = new AbortController();
      const signal = this.aborter.signal;
      const options = {
        stream: this.row.stream || this.stream,
        path: this.row.source_path || this.row.path
      };
      if (this.scope) options[this.shelved ? 'shelf' : 'change'] = this.scope;
      try {
        const info = await this.call(
          'file_info',
          {
            ...options,
            ...(this.workspace ? { workspace: this.workspace } : {}),
            preview: this.tab === 'preview'
          },
          signal
        );
        if (generation === this.generation) this.info = info;
      } catch (error) {
        if (generation === this.generation && error.name !== 'AbortError')
          this.error = error.message;
      } finally {
        if (generation === this.generation) this.busy = false;
      }
    }
  }
};
</script>

<template>
  <section class="file-workspace-inspector" :aria-label="t('File details')">
    <WorkspaceInspectorView
      :info="info"
      :preview="info?.preview"
      :tab="tab"
      :busy="busy"
      :error="error"
      @tab="tab = $event"
    />
  </section>
</template>
<style scoped>
.file-workspace-inspector {
  display: flex;
  position: relative;
  min-height: 140px;
  max-height: 300px;
  flex: 0 0 220px;
  border-top: 1px solid var(--outline-variant);
  overflow: hidden;
}
</style>
