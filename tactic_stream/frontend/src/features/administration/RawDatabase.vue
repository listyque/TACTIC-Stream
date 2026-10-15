<script>
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/database/raw.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/database/raw.state.mjs';
import { rawDatabase } from '../../api.js';
import { t } from '../../i18n.js';
import RawCellEditor from './RawCellEditor.vue';
import { cellText, cellValue } from './rawCellValues.js';
export default {
  components: { FrameView, RawCellEditor },
  props: {
    ticket: String,
    project: String,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved'],
  data() {
    return {
      catalog: [],
      identity: '',
      metadata: {},
      revision: '',
      rows: [],
      baseline: '',
      busy: false,
      uncertain: false,
      canWrite: false,
      error: '',
      request: 0,
      ui: State.initial(),
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      controlSize: 36,
      observer: null,
      resizeFrame: 0
    };
  },
  computed: {
    dirty() {
      return (
        this.uncertain ||
        (JSON.stringify(this.rows) !== this.baseline && this.baseline !== '')
      );
    },
    columns() {
      return this.metadata.columns || [];
    },
    editable() {
      return !!this.identity && this.canWrite && !this.busy && !this.uncertain;
    },
    skin() {
      return appearance.theme;
    },
    frameModel() {
      return {
        ready: !!this.identity && this.baseline !== '',
        identity: this.identity,
        catalog: this.catalog,
        metadata: this.metadata,
        rows: this.rows,
        columns: this.columns,
        canWrite: this.canWrite,
        canLoad: !!this.ticket,
        busy: this.busy,
        dirty: this.dirty,
        uncertain: this.uncertain,
        error: this.error,
        controlHeight: this.controlSize
      };
    },
    models() {
      return { rows: this.rows.map((row) => this.columns.map(() => row)) };
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
    }
  },
  mounted() {
    this.load('list');
    this.measure();
    window.addEventListener('beforeunload', this.beforeUnload);
    this.observer = new ResizeObserver((entries) => {
      cancelAnimationFrame(this.resizeFrame);
      this.resizeFrame = requestAnimationFrame(() => {
        for (const entry of entries) {
          if (entry.target === this.$refs.body)
            this.viewport = {
              width: Math.max(1, entry.contentRect.width),
              height: Math.max(1, entry.contentRect.height)
            };
          else this.toolbarSize = entry.contentRect.width;
        }
      });
    });
    this.observer.observe(this.$refs.body);
    this.observer.observe(
      this.toolbarTarget
        ? document.querySelector(this.toolbarTarget) || this.$el
        : this.$el
    );
  },
  beforeUnmount() {
    this.request++;
    this.observer?.disconnect();
    cancelAnimationFrame(this.resizeFrame);
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  watch: {
    project() {
      this.reset();
    },
    ticket() {
      this.reset();
    },
    skin() {
      this.$nextTick(this.measure);
    }
  },
  methods: {
    t,
    measure() {
      this.controlSize =
        parseFloat(
          getComputedStyle(this.$el).getPropertyValue('--control-height')
        ) || 36;
    },
    cellScene(node, record, row, column) {
      return UI.cell(
        node,
        record,
        row,
        column,
        this.frameModel,
        this.ui,
        appearance.language
      );
    },
    async dispatch(event) {
      const result = State.transition(this.ui, this.frameModel, event);
      this.ui = result.ui;
      for (const command of result.commands) {
        switch (command.type) {
          case 'select':
            this.select(command.identity);
            break;
          case 'add':
            this.add();
            break;
          case 'deleteRow':
            this.rows[command.row].deleted = !this.rows[command.row].deleted;
            break;
          case 'cell':
            this.openCell(
              command.row,
              this.columns.find((column) => column.name === command.name)
            );
            break;
          case 'page':
            this.page(command.offset);
            break;
          case 'drop':
            this.drop(command.name);
            break;
          case 'export':
            await this.load('export');
            break;
          case 'save':
            await this.save();
            break;
          case 'reload':
            await this.load('list');
            break;
          case 'discard':
            this.discard();
            break;
          case 'focusGrid':
            await this.$nextTick();
            await this.$refs.frame.focusGrid(
              command.grid,
              command.row,
              command.column,
              command.id
            );
            break;
          default:
            throw Error('Unsupported Raw database command: ' + command.type);
        }
      }
    },
    beforeUnload(event) {
      if (this.dirty || this.busy || this.uncertain) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    canLeave() {
      if (this.dirty || this.busy || this.uncertain) {
        this.error = 'Save or discard raw table changes before leaving.';
        return false;
      }
      return true;
    },
    reset() {
      this.$refs.cellEditor?.close();
      this.request++;
      this.busy = false;
      this.identity = '';
      this.rows = [];
      this.baseline = '';
      this.metadata = {};
      this.uncertain = false;
      this.ui = State.initial();
      this.load('list');
    },
    async load(action = 'load', extra = {}) {
      if (this.busy) return;
      const request = ++this.request;
      this.busy = true;
      this.error = '';
      try {
        const result = await rawDatabase(action, this.ticket, this.project, {
          identity: this.identity,
          expected_revision: this.revision,
          ...extra
        });
        if (request !== this.request) return;
        if (result.catalog) this.catalog = result.catalog;
        if (result.canWrite !== undefined) this.canWrite = !!result.canWrite;
        if (action === 'list') {
          this.busy = false;
          if (this.catalog.length) {
            this.identity =
              this.catalog.find((row) => row.identity === this.identity)
                ?.identity || this.catalog[0].identity;
            return this.load();
          }
          this.identity = '';
          this.metadata = {};
          this.rows = [];
          this.baseline = '';
          this.uncertain = false;
        } else if (action === 'export') {
          const url = URL.createObjectURL(
            new Blob(['\uFEFF', result.metadata.csv], {
              type: 'text/csv;charset=utf-8'
            })
          );
          const link = document.createElement('a');
          link.href = url;
          link.download = this.metadata.label.replaceAll(' / ', '_') + '.csv';
          link.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        } else {
          this.identity = result.identity;
          this.metadata = result.metadata;
          this.revision = result.revision;
          this.rows = (result.document.rows || []).map((row) => ({
            ...row,
            deleted: false,
            texts: Object.fromEntries(
              Object.entries(row.values).map(([name, value]) => [
                name,
                cellText(value)
              ])
            ),
            modes: Object.fromEntries(
              Object.entries(row.values).map(([name, value]) => [
                name,
                value === null ? 'null' : 'value'
              ])
            )
          }));
          this.baseline = JSON.stringify(this.rows);
          this.uncertain = false;
          if (['save', 'drop'].includes(action)) this.$emit('saved');
        }
      } catch (error) {
        if (request === this.request) {
          this.error = error.message;
          if (['save', 'drop'].includes(action)) this.uncertain = true;
        }
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    select(identity) {
      if (!this.dirty && !this.busy && !this.uncertain) {
        this.identity = identity;
        this.load();
      }
    },
    page(offset) {
      if (this.canLeave()) this.load('load', { item_offset: offset });
    },
    add() {
      if (this.editable)
        this.rows.push({ key: null, texts: {}, modes: {}, deleted: false });
    },
    cellMode(row, name) {
      return row.modes[name] || (row.key === null ? 'default' : 'value');
    },
    cellDisplay(row, name) {
      const mode = this.cellMode(row, name);
      return mode === 'null'
        ? 'NULL'
        : mode === 'default'
          ? 'DEFAULT'
          : row.texts[name] || '';
    },
    openCell(index, column) {
      const row = this.rows[index];
      if (this.busy || row.deleted) return;
      this.$refs.cellEditor.open({
        index,
        name: column.name,
        type: column.type,
        text: row.texts[column.name] || '',
        mode: this.cellMode(row, column.name),
        newRow: row.key === null,
        rowNumber: this.metadata.offset + index + 1,
        identity: this.identity,
        generation: this.request,
        readonly: !!(
          !this.editable ||
          column.readonly ||
          row.readonly?.includes(column.name)
        )
      });
    },
    applyCell(cell) {
      if (
        !this.editable ||
        cell.identity !== this.identity ||
        cell.generation !== this.request ||
        !this.rows[cell.index] ||
        this.rows[cell.index].deleted
      )
        return;
      this.rows[cell.index].texts[cell.name] = cell.text;
      this.rows[cell.index].modes[cell.name] = cell.mode;
    },
    async save() {
      if (!this.editable || !this.dirty) return;
      try {
        const baseline = JSON.parse(this.baseline);
        const rows = this.rows
          .map((row, index) => {
            const values = Object.fromEntries(
              this.columns
                .filter(
                  (column) =>
                    !column.readonly &&
                    !row.readonly?.includes(column.name) &&
                    this.cellMode(row, column.name) !== 'default' &&
                    (row.key === null ||
                      row.deleted ||
                      row.texts[column.name] !==
                        baseline[index]?.texts[column.name] ||
                      row.modes[column.name] !==
                        baseline[index]?.modes[column.name])
                )
                .map((column) => [
                  column.name,
                  row.deleted
                    ? null
                    : cellValue(
                        row.texts[column.name] || '',
                        column.type,
                        this.cellMode(row, column.name)
                      )
                ])
            );
            if (row.key !== null && !row.deleted && !Object.keys(values).length)
              return null;
            return {
              key: row.key,
              revision: row.revision,
              deleted: row.deleted,
              values
            };
          })
          .filter((row) => row !== null);
        await this.load('save', {
          document: { rows, offset: this.metadata.offset }
        });
      } catch {
        this.error = 'Enter a valid value for the column type.';
      }
    },
    discard() {
      this.ui.confirmation = '';
      this.error = '';
      if (this.uncertain) this.load('list');
      else this.rows = JSON.parse(this.baseline);
    },
    drop(name = this.ui.dropName) {
      if (this.editable && !this.dirty && name === this.metadata.label) {
        this.ui.confirmation = '';
        this.load('drop', { confirmation: name });
      }
    }
  }
};
</script>
<template>
  <section
    class="raw-database frame-host"
    :aria-label="t('Raw database')"
    :aria-busy="busy"
  >
    <Teleport defer :to="toolbarTarget || 'body'" :disabled="!toolbarTarget"
      ><div
        v-show="presentationVisible"
        class="frame-toolbar-host"
        :style="{ width: toolbarSize + 'px' }"
      >
        <FrameView :scene="toolbarScene" @event="dispatch" /></div
    ></Teleport>
    <div ref="body" class="frame-host-body">
      <FrameView
        ref="frame"
        :scene="frameScene"
        :models="models"
        :describe-cell="cellScene"
        @event="dispatch"
      />
    </div>
    <RawCellEditor ref="cellEditor" :busy="busy" @applied="applyCell" />
  </section>
</template>
