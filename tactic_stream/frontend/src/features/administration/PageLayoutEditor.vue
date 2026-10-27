<script>
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { randomUuid } from '../../controls/identity.js';
import { projectPath } from '../workspace/links.js';
import FrameView from '../../frame/FrameView.vue';
import CustomLayoutView from '../interface/CustomLayoutView.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/page.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs';
export default {
  components: { FrameView },
  props: {
    ticket: String,
    project: String,
    searchTypes: Array,
    initialFocus: String,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved', 'card'],
  data() {
    return {
      ui: State.initial(),
      catalog: [],
      document: null,
      baseline: '',
      revision: '',
      compiled: null,
      checkedDocument: '',
      error: '',
      message: '',
      busy: false,
      uncertain: false,
      canWrite: false,
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      observer: null,
      generation: 0,
      previewSerial: 0,
      previewTimer: null,
      previewInFlight: false,
      previewAgain: false,
      pendingSave: null,
      previewKey: '',
      closed: false
    };
  },
  computed: {
    dirty() {
      return (
        (!!this.document && JSON.stringify(this.document) !== this.baseline) ||
        Object.keys(this.ui.text).length > 0 ||
        this.uncertain
      );
    },
    frameModel() {
      return UI.model(
        {
          document: this.document || {},
          catalog: this.catalog,
          dirty: this.dirty,
          busy: this.busy,
          uncertain: this.uncertain,
          canWrite: this.canWrite,
          canLoad: !!this.ticket,
          checked:
            !!this.document &&
            JSON.stringify(this.document) === this.checkedDocument,
          error: this.error,
          message: this.message,
          searchTypes: (this.searchTypes || []).map((row) => ({
            value: row.search_type,
            label: row.title || row.search_type
          }))
        },
        this.ui
      );
    },
    scene() {
      return UI.describe(
        this.frameModel,
        this.ui,
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    },
    toolbar() {
      return UI.toolbar(
        this.frameModel,
        this.ui,
        this.toolbarSize,
        appearance.language
      );
    },
    models() {
      return UI.models(this.frameModel);
    },
    views() {
      return {
        pagePreview: {
          component: CustomLayoutView,
          nodeProps: true,
          props: {
            model: this.compiled || { layoutNodes: [] },
            ticket: this.ticket,
            project: this.project,
            editing: true,
            selectedBlock: this.ui.selected,
            onLoaded: (value) => this.sampleLoaded(value),
            onBlock: (key) => this.dispatch({ type: 'select', key }),
            onGeometry: (value, boxes) =>
              this.dispatch({ type: 'geometry', value, boxes })
          }
        }
      };
    }
  },
  mounted() {
    this.observe();
    this.reload();
  },
  beforeUnmount() {
    this.closed = true;
    this.observer?.disconnect();
    this.generation++;
    this.previewSerial++;
    clearTimeout(this.previewTimer);
  },
  watch: {
    project() {
      this.reset();
    },
    ticket() {
      this.reset();
    },
    initialFocus(value) {
      if (value && !this.dirty && !this.busy) this.load(value);
    }
  },
  methods: {
    rowScene(list, row) {
      return UI.row(list, row, this.frameModel, this.ui, appearance.language);
    },
    sampleLoaded(value) {
      if (!this.compiled?.layoutHasDetails) return;
      const key = value.records?.[0]?.__search_key__;
      if (key && (key !== this.previewKey || !this.compiled.layoutDetail)) {
        this.previewKey = key;
        this.schedule();
      }
    },
    observe() {
      this.observer = observeFrameSizes((entries) => {
        for (const entry of entries) {
          if (entry.target === this.$refs.body)
            this.viewport = {
              width: entry.contentRect.width,
              height: entry.contentRect.height
            };
          else this.toolbarSize = entry.contentRect.width;
        }
      });
      this.observer.observe(this.$refs.body);
      this.observer.observe(
        this.toolbarTarget
          ? document.querySelector(this.toolbarTarget)
          : this.$el
      );
    },
    call(
      action,
      values = {},
      scope = { ticket: this.ticket, project: this.project }
    ) {
      return rpc('execute_cmd', [
        { ticket: scope.ticket, project: scope.project },
        'tactic.ui.panel.dashboard_cmd.DashboardCmd',
        { action, project_code: scope.project, ...values }
      ]).then((result) => result.info);
    },
    reset() {
      this.generation++;
      this.previewSerial++;
      clearTimeout(this.previewTimer);
      this.document = null;
      this.compiled = null;
      this.baseline = '';
      this.checkedDocument = '';
      this.catalog = [];
      this.revision = this.error = this.message = '';
      this.ui = State.initial();
      this.pendingSave = null;
      this.previewKey = '';
      this.canWrite = false;
      this.busy = this.uncertain = false;
      if (this.ticket) this.reload();
    },
    canLeave() {
      if (this.dirty || this.busy) {
        this.error = 'Save or discard changes before continuing';
        return false;
      }
      return true;
    },
    async reload(force = false) {
      if (this.busy || (this.dirty && !force)) return;
      if (this.uncertain && this.pendingSave) {
        await this.recover();
        return;
      }
      const generation = ++this.generation,
        scope = { ticket: this.ticket, project: this.project };
      this.busy = true;
      this.error = '';
      try {
        const state = await this.call('read', {}, scope);
        if (generation !== this.generation) return;
        this.catalog = state.dashboards.map((row) => ({
          identity: row.view.slice(10),
          label: row.view.slice(10)
        }));
        this.revision = state.revision;
        this.canWrite = true;
        const name =
          this.document?.name || this.initialFocus || this.catalog[0]?.identity;
        this.document = null;
        this.baseline = '';
        this.compiled = null;
        if (name) {
          const value = await this.call('read', { name }, scope);
          if (generation !== this.generation) return;
          this.document = value.document;
          this.baseline = JSON.stringify(value.document);
          this.revision = value.revision;
          this.ui = State.initial();
        }
      } catch (e) {
        if (generation === this.generation) this.error = e.message;
      } finally {
        if (generation === this.generation) {
          this.busy = false;
          if (this.document) this.schedule();
        }
      }
    },
    async load(name) {
      if (this.busy || this.dirty) return;
      const generation = ++this.generation;
      this.busy = true;
      this.error = '';
      try {
        const value = await this.call('read', { name });
        if (generation !== this.generation) return;
        this.document = value.document;
        this.revision = value.revision;
        this.baseline = JSON.stringify(value.document);
        this.ui = State.initial();
        this.compiled = null;
      } catch (e) {
        if (generation === this.generation) this.error = e.message;
      } finally {
        if (generation === this.generation) {
          this.busy = false;
          this.schedule();
        }
      }
    },
    schedule() {
      if (this.closed) return;
      clearTimeout(this.previewTimer);
      this.previewSerial++;
      this.previewTimer = setTimeout(() => this.preview(), 250);
    },
    async preview() {
      if (this.closed || !this.document || this.busy || this.uncertain) return;
      if (this.previewInFlight) {
        this.previewAgain = true;
        return;
      }
      const generation = this.generation,
        serial = this.previewSerial,
        document = JSON.stringify(this.document),
        scope = { ticket: this.ticket, project: this.project };
      this.previewInFlight = true;
      try {
        const value = await this.call(
          'preview',
          {
            document: JSON.parse(document),
            expected_revision: this.revision,
            detail_key: this.previewKey
          },
          scope
        );
        if (generation === this.generation && serial === this.previewSerial) {
          this.compiled = value.model;
          this.checkedDocument = document;
          this.error = '';
        }
      } catch (e) {
        if (generation === this.generation && serial === this.previewSerial)
          this.error = e.message;
      } finally {
        this.previewInFlight = false;
        if (this.previewAgain || serial !== this.previewSerial) {
          this.previewAgain = false;
          this.schedule();
        }
      }
    },
    async save() {
      if (
        this.busy ||
        this.uncertain ||
        !this.frameModel.saveAllowed ||
        !this.dirty
      )
        return;
      const payload = {
        document: JSON.parse(JSON.stringify(this.document)),
        expected_revision: this.revision
      };
      if (
        !this.pendingSave ||
        JSON.stringify(this.pendingSave.payload) !== JSON.stringify(payload)
      )
        this.pendingSave = { payload, operation_id: randomUuid() };
      const generation = ++this.generation,
        pending = this.pendingSave;
      this.busy = true;
      this.error = '';
      try {
        const saved = await this.call('apply', {
          ...pending.payload,
          operation_id: pending.operation_id
        });
        if (generation !== this.generation) return;
        if (
          saved.status !== 'applied' ||
          saved.operation_id !== pending.operation_id
        )
          throw Error('Invalid save acknowledgement');
        const state = await this.call('read', { name: this.document.name });
        if (generation !== this.generation) return;
        this.document = state.document;
        this.baseline = this.checkedDocument = JSON.stringify(state.document);
        this.revision = state.revision;
        this.compiled = saved.model;
        this.pendingSave = null;
        this.message = 'Layout saved';
        this.$emit('saved', saved);
      } catch (e) {
        if (generation === this.generation) {
          this.uncertain = !e.status || e.status >= 500;
          this.error = this.uncertain
            ? 'The save result is unknown. Refresh before trying again.'
            : e.message;
        }
      } finally {
        if (generation === this.generation) this.busy = false;
      }
    },
    async recover() {
      const generation = this.generation,
        pending = this.pendingSave,
        scope = { ticket: this.ticket, project: this.project };
      this.busy = true;
      try {
        const result = await this.call(
          'operation',
          {
            operation_id: pending.operation_id
          },
          scope
        );
        if (generation !== this.generation) return;
        if (result.status === 'applied') {
          this.uncertain = false;
          this.busy = false;
          await this.reload(true);
        } else {
          this.uncertain = false;
          this.error =
            'No saved result was found. Save again to retry the same operation.';
        }
      } catch (e) {
        if (generation === this.generation) this.error = e.message;
      } finally {
        if (generation === this.generation) this.busy = false;
      }
    },
    async dispatch(event) {
      const result = State.transition(this.ui, this.frameModel, event);
      this.ui = result.ui;
      for (const command of result.commands) {
        switch (command.type) {
          case 'document':
            this.document = command.document;
            this.error = this.message = '';
            this.schedule();
            break;
          case 'load':
            await this.load(command.name);
            break;
          case 'create':
            this.document = {
              name: command.name,
              title: command.title,
              blocks: []
            };
            this.baseline = '';
            this.compiled = null;
            this.checkedDocument = '';
            this.schedule();
            break;
          case 'discard':
            this.document = this.baseline ? JSON.parse(this.baseline) : null;
            this.ui.text = {};
            this.error = '';
            this.schedule();
            break;
          case 'save':
            await this.save();
            break;
          case 'reload':
            await this.reload(command.force);
            break;
          case 'check':
            await this.preview();
            break;
          case 'card':
            this.$emit('card', command);
            break;
          case 'open':
            window.open(
              projectPath(this.project) + 'dashboard/' + this.document.name,
              '_blank',
              'noopener'
            );
            break;
          default:
            throw Error('Unsupported page command: ' + command.type);
        }
      }
    }
  }
};
</script>
<template>
  <section class="page-layout-editor frame-host" :aria-busy="busy">
    <Teleport :to="toolbarTarget || 'body'" :disabled="!toolbarTarget"
      ><div
        v-show="presentationVisible"
        class="frame-toolbar-host"
        :style="{ width: toolbarSize + 'px' }"
      >
        <FrameView :scene="toolbar" @event="dispatch" /></div
    ></Teleport>
    <div ref="body" class="frame-host-body">
      <FrameView
        :scene="scene"
        :models="models"
        :describe-row="rowScene"
        :views="views"
        @event="dispatch"
      />
    </div>
  </section>
</template>
