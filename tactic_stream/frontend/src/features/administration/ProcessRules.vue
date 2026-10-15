<script>
import { observeFrameSizes } from '../../frame/resize.js';
import { nextTick } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import AppIcon from '../../controls/AppIcon.vue';

import FrameView from '../../frame/FrameView.vue';
import AppButton from '../../controls/AppButton.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/workflow/process_rules.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/workflow/process_rules.state.mjs';
export default {
  components: { FrameView, AppButton, AppIcon },
  props: { ticket: String, project: String },
  emits: ['saved'],
  data() {
    return {
      ui: State.initial(),
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      observer: null,
      active: false,
      context: null,
      identity: '',
      revision: '',
      metadata: {},
      document: { rules: [] },
      baseline: '',
      selected: -1,
      busy: false,
      error: '',
      uncertain: false,
      request: 0,
      canWrite: false,
      page: 'trigger',
      object: null,
      objectViewport: { width: 1, height: 1 }
    };
  },
  computed: {
    dirty() {
      return JSON.stringify(this.document) !== this.baseline;
    },
    rule() {
      return this.document.rules[this.selected];
    },
    editable() {
      return (
        this.canWrite && !this.busy && !this.uncertain && !this.rule?.managed
      );
    },
    frameModel() {
      return {
        ready: Array.isArray(this.document.rules),
        canWrite: this.canWrite,
        canLoad: !!this.identity,
        busy: this.busy,
        dirty: this.dirty,
        uncertain: this.uncertain,
        error: this.error,
        message: '',
        identity: this.identity,
        document: this.document,
        metadata: this.metadata,
        selected: this.selected,
        rule: this.rule || {}
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
    objectScene() {
      return UI.objectDetails(
        this.object,
        this.objectViewport.width,
        this.objectViewport.height,
        appearance.language
      );
    },
    models() {
      return UI.models(this.frameModel, this.ui);
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
    this.observer = observeFrameSizes((entries) => {
      for (const entry of entries) {
        if (entry.target === this.$refs.objectBody)
          this.objectViewport = {
            width: Math.max(1, entry.contentRect.width),
            height: Math.max(1, entry.contentRect.height)
          };
        else if (entry.target === this.$refs.body)
          this.viewport = {
            width: Math.max(1, entry.contentRect.width),
            height: Math.max(1, entry.contentRect.height)
          };
        else this.toolbarSize = entry.contentRect.width;
      }
    });
    this.observer.observe(this.$refs.objectBody);
    this.observer.observe(this.$refs.body);
    this.observer.observe(this.$refs.frameRoot);
  },
  beforeUnmount() {
    this.observer?.disconnect();
    this.request++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  watch: {
    ticket() {
      this.request++;
      this.active = false;
      this.$refs.dialog?.close();
    },
    project() {
      this.request++;
      this.active = false;
      this.$refs.dialog?.close();
    }
  },
  methods: {
    t,
    rowScene(list, record) {
      return UI.row(list, record, this.frameModel, appearance.language);
    },
    async dispatch(event) {
      const result = State.transition(this.ui, this.frameModel, event);
      this.ui = result.ui;
      for (const command of result.commands) {
        switch (command.type) {
          case 'select':
            this.page = this.ui.page;
            this.selected = command.index;
            break;
          case 'add':
            this.page = command.kind;
            this.add();
            break;
          case 'field':
            this.rule[command.field] = command.value;
            if (
              command.field === 'event' &&
              command.value !== 'change|sthpw/task|status'
            )
              this.rule.srcStatus = '';
            break;
          case 'target':
            this.setTarget(
              command.process,
              command.enabled === true ? String(command.value) : command.status,
              command.enabled === true || command.value === true
            );
            break;
          case 'output':
            this.setOutput(command.process, command.value);
            break;
          case 'remove':
            this.remove(true);
            break;
          case 'items':
            await this.load(command.offset);
            break;
          case 'object':
            await this.inspect(command.key);
            break;
          case 'save':
            await this.save(true);
            break;
          case 'reload':
            await this.load();
            break;
          case 'discard':
            this.document = JSON.parse(this.baseline);
            this.selected = this.document.rules.findIndex(
              (rule) => rule.kind === this.ui.page
            );
            this.error = '';
            break;
          case 'close':
            this.close(true);
            break;
          default:
            throw Error(
              'Unsupported process dependencies command: ' + command.type
            );
        }
      }
    },
    beforeUnload(event) {
      if (this.active && (this.dirty || this.busy || this.uncertain)) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    accept(result) {
      this.identity = result.identity;
      this.document = result.document;
      this.metadata = result.metadata;
      this.revision = result.revision;
      this.canWrite = result.canWrite;
      this.baseline = JSON.stringify(this.document);
      this.selected = this.document.rules.findIndex(
        (rule) => rule.kind === this.page
      );
      this.uncertain = false;
    },
    async call(action, values = {}) {
      const result = await rpc('execute_cmd', [
        {
          ticket: this.context.ticket,
          project: this.context.project,
          language: 'python'
        },
        'tactic.ui.panel.process_rules_cmd.ProcessRulesCmd',
        {
          action,
          project_code: this.context.project,
          identity: this.identity,
          ...values
        }
      ]);
      return result.info;
    },
    async open(identity) {
      this.context = { ticket: this.ticket, project: this.project };
      this.identity = identity;
      this.active = true;
      this.page = 'trigger';
      this.ui = State.initial();
      await nextTick();
      this.$refs.dialog.showModal();
      await this.load();
    },
    async load(offset = this.metadata.itemOffset || 0) {
      const id = ++this.request;
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('load', { item_offset: offset });
        if (id === this.request) this.accept(result);
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    close(confirmed = false) {
      if (
        this.busy ||
        (!confirmed &&
          (this.dirty || this.uncertain) &&
          !window.confirm(t('Discard unsaved changes?')))
      )
        return;
      this.request++;
      this.active = false;
      this.$refs.dialog.close();
    },
    reload() {
      if (
        !this.busy &&
        (!(this.dirty || this.uncertain) ||
          window.confirm(t('Discard unsaved changes?')))
      )
        this.load();
    },
    selectPage(page) {
      this.page = page;
      this.selected = this.document.rules.findIndex(
        (rule) => rule.kind === page
      );
    },
    add() {
      if (!this.canWrite || this.busy || this.uncertain) return;
      const kind = this.page === 'notification' ? 'notification' : 'trigger';
      this.document.rules.push({
        key: '',
        kind,
        title: '',
        description: '',
        event: 'change|sthpw/task|status',
        scope: 'local',
        action: kind === 'notification' ? 'notification' : 'task_status',
        managed: false,
        srcStatus: '',
        targets: [],
        outputs: [],
        column: '',
        targetStatus: '',
        scriptPath: '',
        classPath: '',
        subject: '',
        body: '',
        mailTo: '',
        mailCc: '',
        loginTicket: false,
        useTemplate: false,
        mode: 'same process,same transaction',
        rules: ''
      });
      this.selected = this.document.rules.length - 1;
      this.page = kind;
    },
    remove(confirmed = false) {
      if (
        this.editable &&
        this.rule &&
        (confirmed || window.confirm(t('Remove this rule from the draft?')))
      ) {
        this.document.rules.splice(this.selected, 1);
        this.selected = this.document.rules.findIndex(
          (rule) => rule.kind === this.page
        );
      }
    },
    setTarget(process, status, enabled) {
      this.rule.targets = this.rule.targets.filter(
        (row) => row.process !== process
      );
      if (enabled) this.rule.targets.push({ process, status });
    },
    setOutput(process, enabled) {
      this.rule.outputs = this.rule.outputs.filter((name) => name !== process);
      if (enabled) this.rule.outputs.push(process);
    },
    async save(confirmed = false) {
      if (!this.canWrite || this.busy || this.uncertain || !this.dirty) return;
      if (
        !confirmed &&
        !window.confirm(
          t(
            'Save process rules? Global rules affect matching processes in other pipelines. Removed rules are deleted; their scripts are kept. Actions are not executed by Save.'
          )
        )
      )
        return;
      const id = this.request;
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('save', {
          document: this.document,
          expected_revision: this.revision
        });
        if (id === this.request) {
          this.accept(result);
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
    async inspect(key) {
      const id = this.request;
      try {
        const result = await rpc('get_by_search_key', [
          {
            ticket: this.context.ticket,
            project: this.context.project,
            language: 'python'
          },
          key
        ]);
        if (id !== this.request || !this.active) return;
        this.object = result;
        await nextTick();
        this.$refs.object.show();
      } catch (error) {
        if (id === this.request) this.error = error.message;
      }
    }
  }
};
</script>

<template>
  <dialog
    v-window="{ kind: 'process_dependencies' }"
    ref="dialog"
    class="configuration-dialog process-rules-editor frame-process-dialog"
    :aria-label="t('Process dependencies')"
    :aria-busy="busy"
    @cancel.prevent.stop="dispatch({ type: 'close' })"
    @keydown.esc.stop
  >
    <header class="configuration-header">
      <div class="configuration-heading">
        <h1>{{ t('Process dependencies') }}</h1>
        <p class="muted">{{ metadata.process }} · {{ metadata.pipeline }}</p>
      </div>
      <AppButton
        label="Close process dependencies"
        icon="close"
        icon-only
        @click="dispatch({ type: 'close' })"
      />
    </header>
    <section ref="frameRoot" class="frame-host process-dependencies-body">
      <div class="frame-toolbar-host" :style="{ width: toolbarSize + 'px' }">
        <FrameView :scene="toolbarScene" @event="dispatch" />
      </div>
      <div ref="body" class="frame-host-body">
        <FrameView
          :scene="frameScene"
          :models="models"
          :describe-row="rowScene"
          @event="dispatch"
        />
      </div>
    </section>
    <dialog
      v-window="{ type: 'window' }"
      ref="object"
      class="record-dialog process-object-details"
      :aria-label="t('Object details')"
    >
      <header>
        <h2>
          {{
            object?.name ||
            object?.title ||
            object?.code ||
            object?.id ||
            t('Object details')
          }}
        </h2>
        <AppButton
          icon="close"
          icon-only
          label="Close"
          @click="$refs.object.close()"
        />
      </header>
      <div ref="objectBody" class="frame-host-body">
        <FrameView :scene="objectScene" @event="$refs.object.close()" />
      </div>
    </dialog>
  </dialog>
</template>
<style scoped>
.frame-process-dialog[open] {
  display: flex;
  flex-direction: column;
}
.process-dependencies-body {
  min-height: 0;
  flex: 1;
}
.process-object-details[open] {
  display: flex;
  flex-direction: column;
  height: min(700px, 90dvh);
}
</style>
