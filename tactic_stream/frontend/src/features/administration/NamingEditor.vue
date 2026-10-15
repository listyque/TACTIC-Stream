<script>
import { observeFrameSizes } from '../../frame/resize.js';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';

import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/naming/naming.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/naming/naming.state.mjs';
const fields = State.fields,
  flags = State.flags;
const sessionFields = [
  'rules',
  'items',
  'itemCount',
  'itemOffset',
  'identity',
  'document',
  'baseline',
  'revision',
  'uncertain',
  'error',
  'message',
  'context',
  'preview',
  'sample'
];
export default {
  components: { FrameView },
  props: {
    ticket: String,
    project: String,
    searchType: String,
    targetTitle: String,
    session: Object,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved'],
  data() {
    const state = {
      restored: false,
      rules: [],
      items: [],
      itemCount: 0,
      itemOffset: 0,
      identity: '',
      document: null,
      baseline: '',
      revision: '',
      busy: false,
      uncertain: false,
      error: '',
      message: '',
      context: null,
      request: 0,
      preview: null,
      ui: State.initial(),
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      observer: null,
      sample: {
        key: '',
        file: 'example.ma',
        version: 1,
        process: 'publish',
        context: 'publish',
        fileType: 'main',
        snapshotType: 'file'
      }
    };
    const saved = this.session?.snapshot;
    if (
      saved?.context?.ticket === this.ticket &&
      saved.context.project === this.project &&
      saved.context.searchType === this.searchType
    )
      Object.assign(state, saved, { restored: true });
    return state;
  },
  computed: {
    dirty() {
      return (
        this.uncertain ||
        (this.document !== null &&
          (JSON.stringify(this.document) !== this.baseline ||
            State.pending(this.ui)))
      );
    },
    editable() {
      return !this.busy && !this.uncertain;
    },
    frameModel() {
      return {
        ready: !!this.document,
        canWrite: !!this.searchType,
        canLoad: !!this.ticket,
        busy: this.busy,
        dirty: this.dirty,
        uncertain: this.uncertain,
        error: this.error,
        message: this.message,
        identity: this.identity,
        document: this.document || {},
        rules: this.rules,
        items: this.items,
        itemCount: this.itemCount,
        itemOffset: this.itemOffset,
        sample: this.sample,
        previewMode: 'server',
        previewResults: this.preview?.results || [],
        project: this.project,
        searchType: this.searchType,
        targetTitle: this.targetTitle || this.searchType
      };
    },
    frameScene() {
      return UI.describe(
        this.frameModel,
        this.ui,
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    },
    toolbarScene() {
      return UI.toolbar(
        this.frameModel,
        this.ui,
        this.toolbarSize,
        appearance.language
      );
    },
    models() {
      return { namingRules: this.rules };
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
    if (!this.restored) this.reload();
    this.observer = observeFrameSizes((entries) => {
      for (const entry of entries) {
        if (entry.target === this.$refs.body)
          this.viewport = {
            width: Math.max(1, entry.contentRect.width),
            height: Math.max(1, entry.contentRect.height)
          };
        else this.toolbarSize = entry.contentRect.width;
      }
    });
    this.observer.observe(this.$refs.body);
    this.observer.observe(
      this.toolbarTarget
        ? document.querySelector(this.toolbarTarget) || this.$el
        : this.$el
    );
  },
  beforeUnmount() {
    this.applyText();
    if (this.session)
      this.session.snapshot = Object.fromEntries(
        sessionFields.map((key) => [key, this[key]])
      );
    this.observer?.disconnect();
    this.request++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  watch: {
    ticket() {
      this.contextChanged();
    },
    project() {
      this.contextChanged();
    },
    searchType() {
      this.contextChanged();
    },
    document: {
      deep: true,
      handler(value, previous) {
        this.preview = null;
        if (this.dirty && value === previous) this.message = '';
      }
    },
    sample: {
      deep: true,
      handler() {
        this.preview = null;
      }
    }
  },
  methods: {
    t,
    rowScene(node, record) {
      return UI.row(node, record, this.frameModel, appearance.language);
    },
    applyText() {
      for (const [field, value] of Object.entries(this.ui.text))
        this.document[field] = value;
      this.ui = State.transition(this.ui, this.frameModel, {
        type: 'applied'
      }).ui;
    },
    async dispatch(event) {
      const result = State.transition(this.ui, this.frameModel, event);
      this.ui = result.ui;
      for (const command of result.commands) {
        if (!['reload', 'discard'].includes(command.type)) this.applyText();
        switch (command.type) {
          case 'apply':
            break;
          case 'field':
            this.document[command.field] = command.value;
            break;
          case 'sample':
            this.sample[command.field] = command.value;
            break;
          case 'select':
            this.select(
              this.rules.find((row) => row.identity === command.identity),
              true
            );
            break;
          case 'create':
            this.create(false, true);
            break;
          case 'duplicate':
            this.create(true, true);
            break;
          case 'reload':
            await this.reload(0, false, true);
            break;
          case 'discard':
            this.document = this.identity
              ? {
                  ...this.rules.find((row) => row.identity === this.identity)
                    ?.document
                }
              : null;
            this.baseline = JSON.stringify(this.document);
            this.preview = null;
            this.ui = { ...this.ui, text: {} };
            if (this.uncertain) await this.reload(0, false, true);
            break;
          case 'save':
            await this.save(true);
            break;
          case 'evaluate':
            await this.evaluate(command.execute, true);
            break;
          case 'items':
            await this.reload(command.offset, true, true);
            break;
          default:
            throw Error('Unsupported Naming command: ' + command.type);
        }
        this.ui = State.completed(this.ui, command);
      }
    },
    beforeUnload(event) {
      if (this.dirty || this.busy || this.uncertain) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    canLeave() {
      return (
        !this.busy &&
        (!(this.dirty || this.uncertain) ||
          window.confirm(t('Discard unsaved naming changes?')))
      );
    },
    title(row) {
      return (
        row.document.context ||
        row.document.script_path ||
        (row.document.latest_versionless || row.document.current_versionless
          ? t('Versionless')
          : t('Default'))
      );
    },
    async call(action, values = {}) {
      const result = await rpc('execute_cmd', [
        {
          ticket: this.context.ticket,
          project: this.context.project,
          language: 'python'
        },
        'tactic.ui.panel.naming_cmd.NamingCmd',
        {
          action,
          project_code: this.context.project,
          search_type: this.context.searchType,
          ...values
        }
      ]);
      return result.info;
    },
    contextChanged() {
      this.request++;
      this.busy = false;
      this.document = null;
      this.baseline = 'null';
      this.identity = '';
      this.sample.key = '';
      this.uncertain = false;
      this.ui = State.initial();
      this.reload();
    },
    select(row, confirmed = false) {
      if (row?.identity === this.identity || (!confirmed && !this.canLeave()))
        return;
      this.identity = row?.identity || '';
      this.document = row ? { ...row.document } : null;
      this.baseline = JSON.stringify(this.document);
      this.preview = null;
      this.error = '';
      this.message = '';
    },
    accept(result, preserve = false) {
      this.rules = result.rules;
      this.items = result.items;
      this.itemCount = result.itemCount;
      this.itemOffset = result.itemOffset;
      this.revision = result.revision;
      this.uncertain = false;
      if (!preserve) {
        const row =
          this.rules.find((item) => item.identity === result.identity) ||
          this.rules[0];
        this.identity = row?.identity || '';
        this.document = row ? { ...row.document } : null;
        this.baseline = JSON.stringify(this.document);
      }
      if (!this.sample.key && this.items.length)
        this.sample.key = this.items[0].key;
      this.preview = null;
    },
    async reload(offset = 0, preserve = false, confirmed = false) {
      if (this.busy || (!preserve && !confirmed && !this.canLeave())) return;
      const id = ++this.request;
      this.context = {
        ticket: this.ticket,
        project: this.project,
        searchType: this.searchType
      };
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('load', { object_offset: offset });
        if (id === this.request) this.accept(result, preserve);
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    create(duplicate = false, confirmed = false) {
      if (!this.editable || (!confirmed && !this.canLeave())) return;
      const copy =
        duplicate && this.document
          ? { ...this.document }
          : Object.fromEntries(
              fields.map((key) => [key, flags.includes(key) ? false : ''])
            );
      if (!duplicate)
        Object.assign(copy, {
          search_type: this.searchType,
          context: this.sample.context,
          checkin_type: 'strict',
          dir_naming:
            '{project.code}/{search_type.table_name}/{sobject.code}/{snapshot.context}/versions',
          file_naming: '{sobject.name}_v{version}.{ext}'
        });
      this.identity = '';
      this.document = copy;
      this.baseline = '';
      this.preview = null;
      this.error = '';
      this.message = duplicate
        ? 'Duplicated rule is local until Save is pressed.'
        : 'New rule is local until Save is pressed.';
    },
    async save(confirmed = false) {
      if (!this.editable || !this.dirty || !this.document) return;
      if (
        !confirmed &&
        this.identity &&
        !window.confirm(
          t(
            'Update project naming rule? This changes future check-ins in the current project. Existing files are kept.'
          )
        )
      )
        return;
      const id = this.request;
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('save', {
          identity: this.identity,
          document: this.document,
          expected_revision: this.revision,
          object_offset: this.itemOffset
        });
        if (id === this.request) {
          this.accept(result);
          this.message = 'Naming rule saved.';
          this.$emit('saved');
        }
      } catch (error) {
        if (id === this.request) {
          this.uncertain = !error.status || error.status >= 500;
          this.error = this.uncertain
            ? 'The save result is unknown. Refresh before trying again.'
            : error.message;
        }
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    async evaluate(allowExecution = false, confirmed = false) {
      if (!this.editable || !this.document || !this.sample.key) return;
      if (
        !confirmed &&
        allowExecution &&
        !window.confirm(
          t(
            'Run custom naming code? This uses the normal server environment, not an isolated sandbox. Scripts and classes can change data or files.'
          )
        )
      )
        return;
      const id = this.request;
      this.busy = true;
      this.error = '';
      this.preview = null;
      try {
        const result = await this.call('preview', {
          identity: this.identity,
          document: this.document,
          sample: this.sample,
          allow_execution: allowExecution
        });
        if (id === this.request) this.preview = result;
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    }
  }
};
</script>

<template>
  <section
    class="naming-editor frame-host"
    :aria-label="t('Naming editor')"
    :aria-busy="busy"
  >
    <Teleport :to="toolbarTarget || 'body'" :disabled="!toolbarTarget"
      ><div
        v-show="presentationVisible"
        class="frame-toolbar-host"
        :style="{ width: toolbarSize + 'px' }"
      >
        <FrameView :scene="toolbarScene" @event="dispatch" /></div
    ></Teleport>
    <div ref="body" class="frame-host-body">
      <FrameView
        :scene="frameScene"
        :models="models"
        :describe-row="rowScene"
        @event="dispatch"
      />
    </div>
  </section>
</template>
