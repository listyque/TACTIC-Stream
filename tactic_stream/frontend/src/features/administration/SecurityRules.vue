<script>
import { observeFrameSizes } from '../../frame/resize.js';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/security/security.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/security/security.state.mjs';
import { securityRules } from '../../api.js';
import { t } from '../../i18n.js';
import {
  rules,
  parseRules,
  changeRule,
  matrix,
  matrixScopes,
  restoreOriginalXml
} from './securityRules.js';
export default {
  components: { FrameView },
  props: {
    ticket: String,
    project: String,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved'],
  data() {
    return {
      document: null,
      metadata: {},
      baseline: '',
      revision: '',
      context: null,
      group: '',
      pendingGroup: '',
      selected: -1,
      ui: State.initial(),
      busy: false,
      uncertain: false,
      canWrite: false,
      error: '',
      message: '',
      request: 0,
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      observer: null
    };
  },
  computed: {
    scope: {
      get() {
        return this.ui.scope;
      },
      set(value) {
        this.ui.scope = value;
      }
    },
    page: {
      get() {
        return this.ui.page;
      },
      set(value) {
        this.ui.page = value;
      }
    },
    editing: {
      get() {
        return this.ui.editing;
      },
      set(value) {
        this.ui.editing = value;
      }
    },
    selectedCell: {
      get() {
        return this.ui.selectedCell;
      },
      set(value) {
        this.ui.selectedCell = value;
      }
    },
    query() {
      return this.ui.query;
    },
    groupQuery() {
      return this.ui.groupQuery;
    },
    dirty() {
      return (
        !!this.document &&
        (JSON.stringify(this.document) !== this.baseline ||
          State.pending(this.ui))
      );
    },
    editable() {
      return (
        !!this.document &&
        this.canWrite &&
        this.context?.ticket === this.ticket &&
        this.context?.project === this.project &&
        !this.busy &&
        !this.uncertain
      );
    },
    matrixScope() {
      return matrixScopes.includes(this.scope);
    },
    groups() {
      return (this.metadata.groups || []).filter(
        (group) => this.document?.groups[group.identity]
      );
    },
    groupDocument() {
      return this.document?.groups[this.group];
    },
    records() {
      try {
        return this.groupDocument ? rules(this.groupDocument.xml) : [];
      } catch {
        return [];
      }
    },
    attributes() {
      const { ruleIndex, ...attrs } =
        this.records.find((record) => record.ruleIndex === this.selected) || {};
      return attrs;
    },
    matrixTargets() {
      return (this.metadata.targets?.[this.scope] || []).filter(
        (item) =>
          !this.query ||
          JSON.stringify(item)
            .toLowerCase()
            .includes(this.query.trim().toLowerCase())
      );
    },
    matrixGroups() {
      return this.groups.filter((group) =>
        group.label.toLowerCase().includes(this.groupQuery.trim().toLowerCase())
      );
    },
    cells() {
      if (!this.document || !this.matrixScope) return [];
      try {
        return matrix(
          this.document,
          this.metadata,
          this.scope,
          this.project,
          this.matrixTargets,
          this.matrixGroups
        );
      } catch {
        return [];
      }
    },
    cell() {
      return this.selectedCell
        ? this.cells[this.selectedCell.column]?.[this.selectedCell.row]
        : null;
    },
    frameModel() {
      return {
        ready:
          !!this.document &&
          this.context?.ticket === this.ticket &&
          this.context?.project === this.project,
        canWrite: this.canWrite && !!this.groupDocument,
        canLoad: !!this.ticket && !!this.project,
        busy: this.busy,
        dirty: this.dirty,
        uncertain: this.uncertain,
        pendingText: State.pending(this.ui),
        error: this.error,
        message: this.message,
        group: this.group,
        groups: this.groups,
        groupDocument: this.groupDocument || {},
        groupDocuments: this.document?.groups || {},
        records: this.records,
        attributes: this.attributes,
        selected: this.selected,
        metadata: this.metadata,
        matrixRows: this.matrixTargets,
        matrixGroups: this.matrixGroups,
        selectedCell: this.cell,
        xmlSource: this.groupDocument?.xml || '',
        jsonSource: JSON.stringify(this.attributes, null, 2),
        inheritedSource:
          this.metadata.globalDefaultRulesByLevel?.[
            this.groupDocument?.accessLevel
          ] || ''
      };
    },
    models() {
      return {
        ...UI.models(this.frameModel, this.ui, appearance.language),
        matrix: this.matrixTargets.map((_, row) =>
          this.matrixGroups.map((_, column) => this.cells[column]?.[row] || {})
        )
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
    }
  },
  watch: {
    project() {
      this.reload();
    },
    ticket() {
      this.request++;
      this.busy = false;
      this.document = null;
      this.ui = State.initial();
      this.reload(true);
    }
  },
  mounted() {
    this.reload();
    window.addEventListener('beforeunload', this.beforeUnload);
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
    this.request++;
    this.observer?.disconnect();
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    async inspectUser(login) {
      if (this.dirty || this.busy || this.uncertain || !this.context) return;
      const request = ++this.request,
        context = { ...this.context };
      this.busy = true;
      this.error = '';
      try {
        const result = await securityRules(
          'effective',
          context.ticket,
          context.project,
          { login }
        );
        if (
          request !== this.request ||
          this.ticket !== context.ticket ||
          this.project !== context.project
        )
          return;
        this.accept(result);
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    setToolPolicy({ scope, mode, names }) {
      if (
        !this.editable ||
        !this.groupDocument ||
        !['agent_tool', 'mcp_tool'].includes(scope) ||
        !['inherit', 'selected', 'all'].includes(mode)
      )
        return;
      const catalog =
        this.metadata[scope === 'mcp_tool' ? 'mcpTools' : 'agentTools'] || [];
      if (names.some((name) => !catalog.some((tool) => tool.name === name)))
        return;
      const root = parseRules(this.groupDocument.xml);
      for (const rule of [...root.children])
        if (
          (rule.getAttribute('group') ||
            rule.getAttribute('category') ||
            rule.getAttribute('type')) === scope
        )
          rule.remove();
      let xml = new XMLSerializer().serializeToString(root);
      if (mode !== 'inherit') {
        xml = changeRule(xml, -1, {
          group: scope,
          key: '*',
          access: mode === 'all' ? 'allow' : 'deny'
        });
        if (mode === 'selected')
          for (const name of new Set(names))
            xml = changeRule(xml, -1, {
              group: scope,
              key: name,
              access: 'allow'
            });
      }
      this.groupDocument.xml = xml;
      this.selected = -1;
      this.syncText();
      this.error = this.message = '';
    },
    rowScene(node, record) {
      return UI.row(
        node,
        record,
        this.frameModel,
        this.ui,
        appearance.language
      );
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
          case 'effectiveUser':
            await this.inspectUser(command.login);
            break;
          case 'toolPolicy':
            this.setToolPolicy(command);
            break;
          case 'filterMatrix':
            break;
          case 'group':
            this.selectGroup(command.value);
            break;
          case 'matrix':
            this.changeCell(command.column, command.row);
            break;
          case 'inherit':
            this.changeCell(command.column, command.row, true);
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
          case 'focus':
            await this.$nextTick();
            if (!this.$refs.frame.focusControl(command.id))
              this.$refs.frame.focusControl(command.fallback);
            break;
          case 'selectRule':
            this.selectRule(command.index);
            break;
          case 'addRule':
            this.addRule(command.scope);
            break;
          case 'removeRule':
            this.setRule(this.selected);
            break;
          case 'attribute':
            this.setAttribute(command.field, String(command.value));
            break;
          case 'target':
            this.setRule(this.selected, {
              ...this.attributes,
              ...command.attributes
            });
            break;
          case 'groupField':
            this.groupDocument[command.field] = command.value;
            break;
          case 'ruleAccess': {
            const { ruleIndex, ...attrs } =
              this.records.find(
                (record) => record.ruleIndex === command.index
              ) || {};
            this.setRule(command.index, { ...attrs, access: command.value });
            break;
          }
          case 'applyText':
            this.applyText(command);
            break;
          case 'save':
            await this.save();
            break;
          case 'reload':
            await this.reload(command.force);
            break;
          case 'discard':
            this.ui.text = this.ui.baseline = '';
            this.document = JSON.parse(this.baseline);
            this.selected = this.records[0]?.ruleIndex ?? -1;
            this.syncText();
            this.error = this.message = '';
            break;
          default:
            throw Error('Unsupported Access rules command: ' + command.type);
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
      if (this.busy) return false;
      if (this.dirty || this.uncertain) {
        this.error = '';
        this.dispatch({ type: 'discard' });
        return false;
      }
      return true;
    },
    accept(result) {
      this.ui.text = this.ui.baseline = '';
      this.canWrite = result.canWrite !== false;
      this.document = result.document;
      this.metadata = result.metadata;
      this.revision = result.revision;
      this.baseline = JSON.stringify(this.document);
      if (this.pendingGroup) {
        this.group = this.pendingGroup;
        this.pendingGroup = '';
        if (!this.groups.some((group) => group.identity === this.group)) {
          this.group = '';
          this.selectGroup('');
          throw new Error('Group is no longer available');
        }
      }
      this.group = this.groups.some((group) => group.identity === this.group)
        ? this.group
        : this.groups[0]?.identity || '';
      this.selectGroup(this.group);
      for (const group of Object.values(this.document.groups))
        parseRules(group.xml);
    },
    async reload(force = false) {
      if (this.busy) return;
      if (this.dirty && !force) {
        this.dispatch({ type: 'reload' });
        return;
      }
      const request = ++this.request,
        context = { ticket: this.ticket, project: this.project };
      if (
        this.context &&
        (this.context.ticket !== context.ticket ||
          this.context.project !== context.project)
      ) {
        this.document = null;
        this.baseline = '';
        this.ui = State.initial();
      }
      this.context = context;
      this.busy = true;
      this.error = '';
      this.message = '';
      try {
        const result = await securityRules(
          'read',
          context.ticket,
          context.project
        );
        if (
          request !== this.request ||
          context.ticket !== this.ticket ||
          context.project !== this.project
        )
          return;
        this.context = context;
        this.uncertain = false;
        this.ui.confirmation = '';
        this.accept(result);
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    pendingText() {
      return State.pending(this.ui);
    },
    focusGroup(code) {
      if (this.dirty || this.uncertain)
        throw new Error('Apply or discard unsaved changes first');
      if (this.document?.groups[code]) this.selectGroup(code);
      else if (this.document && !this.busy)
        throw new Error('Group is no longer available');
      else {
        this.pendingGroup = code;
        this.group = code;
      }
    },
    selectGroup(code) {
      if (this.pendingText() && code !== this.group) {
        this.error =
          'Apply or discard the text draft before changing the selection.';
        return;
      }
      this.group = code;
      this.selected = this.records[0]?.ruleIndex ?? -1;
      this.syncText();
    },
    syncText() {
      this.ui = State.synchronize(this.ui, this.frameModel, true);
    },
    selectRule(index) {
      if (this.pendingText()) {
        this.error =
          'Apply or discard the text draft before changing the selection.';
        return;
      }
      this.selected = index;
      this.syncText();
      this.editing = true;
    },
    setRule(index, attributes) {
      if (!this.editable || !this.groupDocument) return;
      try {
        this.setGroupXml(
          this.group,
          changeRule(this.groupDocument.xml, index, attributes)
        );
        this.selected =
          index === -1 ? this.records.length - 1 : attributes ? index : -1;
        this.syncText();
        this.error = '';
        this.message = '';
      } catch (error) {
        this.error = error.message;
      }
    },
    setAttribute(name, value) {
      this.setRule(this.selected, { ...this.attributes, [name]: value });
    },
    setGroupXml(identity, xml) {
      this.document.groups[identity].xml = restoreOriginalXml(
        JSON.parse(this.baseline).groups[identity]?.xml,
        xml
      );
    },
    addRule(scope = this.scope) {
      if (this.pendingText()) return;
      const targetScope = scope === 'tasks' ? 'process' : scope || this.scope;
      const defaults = {
        project: { code: '*' },
        search_type: { code: '*' },
        process: { process: '*', pipeline: '*' },
        link: { element: '*' },
        builtin: { key: 'view_side_bar' },
        sobject: { key: '*' },
        sobject_column: { search_type: '*', column: '*' },
        gear_menu: { submenu: '*', label: '*' },
        search_filter: { search_type: '', column: '', op: '=', value: '' }
      };
      const attrs = {
        group: targetScope,
        access: 'deny',
        ...(defaults[targetScope] || { key: '*' })
      };
      if (!['project', 'builtin'].includes(targetScope))
        attrs.project = this.project;
      if (targetScope === 'search_filter') delete attrs.access;
      this.setRule(-1, attrs);
      this.editing = true;
    },
    changeCell(column, row, inherit = false) {
      if (!this.editable || this.pendingText()) return;
      const cell = this.cells[column][row];
      if (cell.custom || (!inherit && cell.locked)) return;
      const settings = this.document.groups[cell.group];
      for (const index of [...cell.ruleIndices].reverse())
        settings.xml = changeRule(settings.xml, index);
      if (!inherit && (this.scope !== 'script_runner' || cell.checked))
        settings.xml = changeRule(settings.xml, -1, {
          group: this.scope === 'tasks' ? 'process' : this.scope,
          ...this.matrixTargets[row].attributes,
          access: cell.checked ? 'deny' : 'allow'
        });
      this.setGroupXml(cell.group, settings.xml);
      this.selectedCell = { column, row };
      if (this.group === cell.group) this.syncText();
      this.error = '';
      this.message = '';
    },
    applyText(command) {
      if (!this.editable) return;
      const page = command?.page || this.page;
      const text = command?.text ?? this.ui.text;
      try {
        if (page === 'rule') {
          const attrs = JSON.parse(text);
          if (
            !attrs ||
            Array.isArray(attrs) ||
            typeof attrs !== 'object' ||
            Object.values(attrs).some((value) => typeof value !== 'string')
          )
            throw new Error(
              'Attributes must be a JSON object with string values'
            );
          this.setRule(this.selected, attrs);
        } else {
          parseRules(text);
          this.setGroupXml(this.group, text);
          this.selected = -1;
          this.syncText();
          this.error = '';
        }
      } catch (error) {
        this.error =
          error instanceof SyntaxError
            ? 'Attributes must be a JSON object with string values'
            : error.message;
      }
    },
    async save() {
      if (!this.editable || !this.dirty) return;
      if (this.pendingText()) {
        this.error = 'Apply or discard the text draft before saving.';
        return;
      }
      const request = this.request;
      this.busy = true;
      this.error = '';
      this.message = '';
      try {
        const result = await securityRules(
          'save',
          this.context.ticket,
          this.context.project,
          { document: this.document, expected_revision: this.revision }
        );
        if (request !== this.request) return;
        this.accept(result);
        this.message = 'Access rules saved on server';
        this.$emit('saved');
      } catch (error) {
        if (request !== this.request) return;
        this.uncertain = !error.status || error.status >= 500;
        this.error = this.uncertain
          ? 'The save result is unknown. Reload access rules before trying again.'
          : error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    }
  }
};
</script>
<template>
  <section
    class="security-rules frame-host"
    style="gap: 8px"
    :aria-label="t('Access rules')"
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
        :describe-row="rowScene"
        :describe-cell="cellScene"
        @event="dispatch"
      />
    </div>
  </section>
</template>
