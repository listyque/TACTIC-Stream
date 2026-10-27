<script>
import { useId } from 'vue';
import {
  rpc,
  tableCells,
  widgetConfiguration,
  interfaceDefinition,
  uploadFormFile
} from '../../api.js';
import { t } from '../../i18n.js';
import TableCell from './TableCell.vue';
import TableView from './TableView.vue';
import TableDocument from './TableDocument.vue';
import TableServiceDialogs from './TableServiceDialogs.vue';
import TableParentPicker from './TableParentPicker.vue';
import NestedTable from './NestedTable.vue';
import {
  tableDefinition,
  changeTable
} from '../administration/columnsEditor.js';
import ObjectOperations from '../objects/ObjectOperations.vue';
import ObjectAction from '../objects/ObjectAction.vue';
import { copyText } from '../../controls/clipboard.js';
import TableInlineEditor from './TableInlineEditor.vue';
import { fieldKind, unsupportedField } from '../objects/recordFields.js';
import RecordForm from '../objects/RecordForm.vue';
import { asyncComponent } from '../../controls/asyncComponent.js';
const CustomLayoutView = asyncComponent(() => import('./CustomLayoutView.vue'));
const RelatedObjects = asyncComponent(
  () => import('../objects/RelatedObjects.vue')
);
const SnapshotCheckout = asyncComponent(
  () => import('../checkin/SnapshotCheckout.vue')
);
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppSelect from '../../controls/AppSelect.vue';
import AppSearchField from '../../controls/AppSearchField.vue';
import { mobile } from '../../mobile.js';
import FilePreview from '../objects/FilePreview.vue';
import { fileBlob } from '../objects/previewFiles.js';
import NotesPanel from '../objects/NotesPanel.vue';
import TaskTableEditor from './TaskTableEditor.vue';
import JournalDetails from '../journal/JournalDetails.vue';
const ResultPresentation = asyncComponent(
  () => import('../workspace/ResultPresentation.vue')
);
import { groupRecords } from '../workspace/resultViews.js';
import { runTableScript } from './tableScript.js';
import { route as tableActionRoute } from '../../../../src/tactic_stream/shared_ui/features/table/actions.state.mjs';
import { link as tableLink } from '../../../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';

export default {
  name: 'ConfiguredView',
  inject: {
    openTableCheckin: { default: null },
    openTableSecurity: { default: null },
    openTablePort: { default: null }
  },
  components: {
    SnapshotCheckout,
    NestedTable,
    TableServiceDialogs,
    TableParentPicker,
    TableDocument,
    CustomLayoutView,
    RecordForm,
    RelatedObjects,
    TableInlineEditor,
    TableView,
    TableCell,
    ObjectOperations,
    ObjectAction,
    AppButton,
    AppMenu,
    AppSelect,
    AppSearchField,
    FilePreview,
    NotesPanel,
    TaskTableEditor,
    ResultPresentation,
    JournalDetails
  },
  props: {
    definition: Object,
    layoutModel: Object,
    layoutWidth: Number,
    layoutHeight: Number,
    layoutBusy: Boolean,
    ticket: String,
    project: String,
    workspaceId: String,
    active: { type: Boolean, default: true },
    rows: { type: Array, default: null },
    configured: { type: Boolean, default: true },
    readOnly: { type: Boolean, default: true },
    sortField: String,
    sortDirection: String,
    selectedKeys: { type: Array, default: () => [] },
    resultMode: { type: String, default: 'table' },
    groupMode: { type: String, default: 'none' },
    resultState: Object,
    parentKey: String,
    selectionEnabled: { type: Boolean, default: true },
    accent: String
  },
  emits: [
    'loaded',
    'close',
    'sort',
    'inspect',
    'operate',
    'select',
    'column',
    'result-state',
    'focus',
    'result-scroll',
    'saved',
    'organization',
    'filter-apply'
  ],
  setup() {
    return { tabId: useId() };
  },
  data() {
    return {
      selected: '',
      loaded: [],
      busy: false,
      error: '',
      request: 0,
      page: 0,
      pageSize: 50,
      hasNext: false,
      started: false,
      filterField: '',
      filterValue: '',
      filters: [],
      localSortField: '',
      localSortDirection: 'asc',
      cells: {},
      cellsBusy: false,
      cellError: '',
      cellRequest: 0,
      expandedDetails: {},
      expandedTables: {},
      nestedEditor: null,
      taskDrafts: {},
      taskEditor: null,
      taskBusy: false,
      taskError: '',
      taskUncertain: false,
      taskRequest: 0,
      closedGroups: { ...this.resultState?.closedGroups },
      localState: {},
      localSelection: [],
      tableOverride: null,
      tableConfig: null,
      columnBusy: false,
      columnError: '',
      columnUncertain: false,
      columnRequest: 0,
      actionRequest: 0,
      targetOperations: null,
      targetRecord: null,
      targetEditView: 'edit',
      targetIgnore: [],
      targetInsertView: 'insert',
      scriptAbort: null,
      serviceDocument: null,
      documentRequest: 0,
      serviceBusy: false,
      serviceMessage: '',
      relatedVisited: false,
      checkoutVisited: false,
      checkoutProject: '',
      cellEditor: null,
      editRequest: 0,
      editBusy: false,
      editError: '',
      editUncertain: false,
      taskContext: null,
      hoveredTaskCell: null
    };
  },
  computed: {
    mobile() {
      return mobile.value;
    },
    displayedMode() {
      return this.table.item_layout
        ? {
            grid: 'tiles',
            list: 'list',
            tree: 'continious',
            table: 'layout_table'
          }[this.table.item_layout.collection]
        : this.mobile && this.workspaceId
          ? 'continious'
          : this.resultMode;
    },
    itemLayout() {
      return this.table.item_layout || null;
    },
    table() {
      return this.tableOverride || this.definition?.table || {};
    },
    tableState() {
      return this.resultState || this.localState;
    },
    tableSelection() {
      return this.ownQuery ? this.localSelection : this.selectedKeys;
    },
    targetProject() {
      if (
        this.targetRecord?.__search_key__?.startsWith('sthpw/snapshot?') &&
        this.targetRecord.project_code
      )
        return this.targetRecord.project_code;
      return this.targetRecord
        ? new URL(
            'skey://' + this.targetRecord.__search_key__
          ).searchParams.get('project') || this.project
        : this.project;
    },
    tableViews() {
      return (
        this.tableConfig?.table_views || [
          {
            view: this.table.view || 'table',
            title: this.table.view || 'table',
            current: true
          }
        ]
      );
    },
    columnEditable() {
      return (
        !this.readOnly &&
        !!this.definition?.administration &&
        !this.columnBusy &&
        !this.columnUncertain &&
        !this.editBusy &&
        !this.editUncertain &&
        !this.taskBusy
      );
    },
    tabs() {
      return (
        this.configured && this.table.layout === 'tactic.ui.container.TabWdg'
      );
    },
    ownQuery() {
      return this.rows === null && !this.tabs && this.supportedLayout;
    },
    columnNames() {
      return Object.keys(this.definition?.columns || {}).filter(
        (name) => !name.startsWith('_tmp')
      );
    },
    pageSizes() {
      return [...new Set([10, 25, 50, 100, 250, 500, this.pageSize])].sort(
        (a, b) => a - b
      );
    },
    activeSortField() {
      return this.rows === null
        ? this.localSortField ||
            this.definition?.panel?.order_by?.[0]?.split(/\s+/)[0]
        : this.sortField;
    },
    activeSortDirection() {
      if (this.rows !== null) return this.sortDirection;
      if (this.localSortField) return this.localSortDirection;
      return (
        this.definition?.panel?.order_by?.[0]?.split(/\s+/)[1]?.toLowerCase() ||
        'asc'
      );
    },
    rowRange() {
      return this.loaded.length
        ? `${this.page * this.pageSize + 1}–${this.page * this.pageSize + this.loaded.length}`
        : '0';
    },
    supportedLayout() {
      return (
        !this.configured ||
        [
          'sobject-layout',
          'tactic.ui.panel.TableLayoutWdg',
          'TableWdg',
          'TableLayoutWdg'
        ].includes(this.table.layout)
      );
    },
    elements() {
      const columns = this.definition?.columns || {};
      if (!this.configured || !this.table.configured) {
        return Object.keys(columns)
          .filter((name) => !name.startsWith('_tmp'))
          .map((name) => ({
            name,
            title: name,
            field: name,
            supported: true,
            sortable: true,
            cell: {
              kind: ['bool', 'boolean'].includes(
                columns[name].data_type?.toLowerCase()
              )
                ? 'boolean'
                : 'text'
            }
          }));
      }
      return (this.table.elements || [])
        .filter(
          (item) =>
            !['true', '1', 'yes', 'on'].includes(
              String(item.attributes?.hidden || '')
                .trim()
                .toLowerCase()
            )
        )
        .map((item) => {
          const cell = item.cell || {
            kind: 'text',
            field: item.name,
            supported: false,
            sortable: false
          };
          const rawWidth = String(item.attributes?.width || '')
            .trim()
            .replace(/px$/, '');
          const hint =
            this.cells[this.records[0]?.__search_key__]?.[item.name]?.widthHint;
          const width = Math.max(
            48,
            Math.min(
              640,
              /^[+-]?\d+$/.test(rawWidth)
                ? Number(rawWidth) || 160
                : hint || 160
            )
          );
          const editable =
            !!this.definition?.operations?.edit && !!cell.editable;
          return {
            ...item,
            field: cell.field,
            sortField: cell.sort_field || cell.field,
            supported: cell.supported,
            sortable: cell.sortable,
            cell,
            width,
            editable,
            kind: cell.kind,
            hideOrder:
              item.attributes?.th_hide_order == null
                ? undefined
                : Number(item.attributes.th_hide_order),
            dataType: columns[cell.field]?.data_type || ''
          };
        });
    },
    records() {
      return this.rows ?? this.loaded;
    },
    rowGroups() {
      const mode = this.tableState.table?.groupMode || this.groupMode;
      if (!mode.startsWith('column:'))
        return groupRecords(
          this.records,
          mode,
          this.$refs.presentation?.nodes || [],
          this.$refs.presentation?.organization || {}
        );
      const name = mode.slice(7),
        groups = new Map();
      for (const record of this.records) {
        const cell = this.displayCells[record.__search_key__]?.[name];
        const parent = cell?.parentGrouping ? cell : null;
        const label = String(cell?.text ?? record[name] ?? '');
        const key = parent ? parent.groupKey : label;
        if (!groups.has(key))
          groups.set(key, {
            key,
            label: label || 'No value',
            cell: parent,
            records: []
          });
        groups.get(key).records.push(record);
      }
      return [...groups.values()].sort((left, right) => {
        if (left.cell || right.cell) {
          if (left.key === right.key) return 0;
          return left.key < right.key ? -1 : 1;
        }
        return left.key.localeCompare(right.key, undefined, {
          numeric: true,
          sensitivity: 'base'
        });
      });
    },
    selectable() {
      return (
        this.selectionEnabled && !this.readOnly && !!this.definition?.operations
      );
    },
    cellContext() {
      return [
        this.records,
        this.table,
        this.configured,
        this.ticket,
        this.project
      ];
    },
    dirtyTaskCount() {
      return Object.keys(this.taskDrafts).length;
    },
    displayCells() {
      if (!this.dirtyTaskCount) return this.cells;
      const cells = { ...this.cells };
      for (const draft of Object.values(this.taskDrafts)) {
        const row = (cells[draft.plan.search_key] = {
          ...cells[draft.plan.search_key]
        });
        for (const [name, cell] of Object.entries(row)) {
          if (!cell.tasks) continue;
          row[name] = {
            ...cell,
            tasks: cell.tasks.map((original) => {
              if (
                original.process !== draft.plan.process ||
                (original.context || original.process) !== draft.plan.context ||
                (original.taskSearchKey || '') !== draft.plan.task_key
              )
                return original;
              const task = {
                ...original,
                status: draft.data.status ?? original.status,
                assigned: draft.data.assigned ?? original.assigned,
                bidStart: draft.data.bid_start_date ?? original.bidStart,
                bidEnd: draft.data.bid_end_date ?? original.bidEnd,
                pending: true
              };
              task.statusColor =
                draft.plan.colors[task.status] || task.statusColor;
              if ('assigned' in draft.data)
                task.assignedIdentity = task.assigned
                  ? {
                      login: task.assigned,
                      displayName:
                        draft.plan.users.find(
                          (user) => user.value === task.assigned
                        )?.label || task.assigned,
                      initials: task.assigned.slice(0, 2).toUpperCase()
                    }
                  : null;
              return task;
            })
          };
        }
      }
      return cells;
    }
  },
  watch: {
    active(value) {
      if (!value) {
        ++this.actionRequest;
        ++this.documentRequest;
        this.scriptAbort?.abort();
        this.scriptAbort = null;
        this.serviceBusy = false;
        this.$refs.tableDocument?.close();
      }
    },
    'resultState.closedGroups': {
      deep: true,
      handler(value) {
        if (JSON.stringify(value || {}) !== JSON.stringify(this.closedGroups))
          this.closedGroups = { ...value };
      }
    },
    closedGroups: {
      deep: true,
      handler(value) {
        if (this.resultMode === 'table')
          this.tableStateChanged({
            ...this.tableState,
            closedGroups: { ...value }
          });
      }
    },
    displayedMode(value) {
      if (value === 'table') {
        this.loadCells();
        this.loadTableConfig();
      }
    },
    cellContext: {
      immediate: true,
      handler(value, previous) {
        this.loadCells(previous);
      }
    },
    definition: {
      immediate: true,
      handler(value, previous) {
        if (
          previous &&
          (previous.search_type !== value.search_type ||
            previous.table?.view !== value.table?.view)
        )
          this.invalidateContext();
        this.columnRequest++;
        this.tableOverride = null;
        this.tableConfig = null;
        this.columnBusy = false;
        this.columnUncertain = false;
        this.selected = this.table.elements?.some(
          (item) => item.name === this.table.selected
        )
          ? this.table.selected
          : this.table.elements?.[0]?.name || '';
        this.reset();
        if (
          this.tableState.table?.view &&
          this.tableState.table.view !== this.table.view
        )
          this.selectTableView(this.tableState.table.view);
        else this.loadTableConfig();
      }
    },
    ticket() {
      this.invalidateContext();
      this.reset();
    },
    project() {
      this.invalidateContext();
      this.reset();
    },
    parentKey() {
      this.invalidateContext();
      this.reset();
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
  },
  beforeUnmount() {
    this.scriptAbort?.abort();
    this.$refs.parentPicker?.close();
    this.$refs.tableServiceDialogs?.close();
    this.request++;
    this.cellRequest++;
    this.taskRequest++;
    this.columnRequest++;
    this.actionRequest++;
    this.editRequest++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    openDependencyFile(result) {
      this.$refs.preview.open(result.snapshot, {
        ...result,
        context: result.snapshot.context,
        version: result.snapshot.version,
        loadFile: fileBlob
      });
    },
    restoreFocus(key) {
      if (this.displayedMode === 'table') {
        const record = this.records.find(
          (record) => record.__search_key__ === key
        );
        if (!record) return false;
        this.$emit('focus', { kind: 'object', record });
        return true;
      }
      const node =
        this.displayedMode !== 'table' && this.$refs.presentation?.selectedNode;
      if (
        !node ||
        (node.ownerKey || node.record?.__search_key__) !== key ||
        (node.kind === 'branch' && node.branch?.kind !== 'process')
      )
        return false;
      this.$emit('focus', node);
      return true;
    },
    t,
    invalidateContext() {
      this.expandedTables = {};
      this.nestedEditor = null;
      this.scriptAbort?.abort();
      this.scriptAbort = null;
      this.$refs.tableServiceDialogs?.close();
      this.$refs.parentPicker?.close();
      this.$refs.tableDocument?.close();
      this.serviceDocument = null;
      this.editRequest++;
      this.actionRequest++;
      this.columnRequest++;
      this.taskRequest++;
      this.columnBusy =
        this.editBusy =
        this.taskBusy =
        this.serviceBusy =
          false;
      this.tableConfig = null;
      this.tableOverride = null;
      if (this.cellEditor) {
        this.editUncertain = true;
        this.editError =
          'Connection context changed. Close this form and reopen it before saving.';
      }
      if (this.dirtyTaskCount) {
        this.taskUncertain = true;
        this.taskError =
          'Connection context changed. Close this form and reopen it before saving.';
      }
    },
    tableStateChanged(value) {
      if (this.resultState) this.$emit('result-state', value);
      else this.localState = value;
    },
    async cellEditCommand(values) {
      if (
        this.cellEditor &&
        (this.cellEditor.context.ticket !== this.ticket ||
          this.cellEditor.context.project !== this.project)
      ) {
        const error = new Error(
          'Connection context changed. Close this form and reopen it before saving.'
        );
        error.status = 400;
        throw error;
      }
      const command = this.cellEditor?.preference
        ? 'tactic.ui.table.SetPreferenceCmd'
        : 'tactic.ui.table.table_edit.TableCellEditCmd';
      return (
        await rpc('execute_cmd', [
          this.cellEditor?.context || {
            ticket: this.ticket,
            project: this.project,
            language: 'python'
          },
          command,
          values
        ])
      ).info;
    },
    async openPreference(record, cell, anchor) {
      if (
        this.editBusy ||
        this.editUncertain ||
        !cell.preferenceKey ||
        !anchor?.isConnected
      )
        return;
      if (this.cellEditor && !window.confirm(t('Discard unsaved changes?')))
        return;
      this.editRequest++;
      this.$refs.inlineEditor.close();
      this.editError = '';
      const options = cell.preferenceOptions || [];
      this.cellEditor = {
        preference: true,
        explicitSave: true,
        preferredWidth: 360,
        plans: [],
        context: {
          ticket: this.ticket,
          project: this.project,
          language: 'python'
        },
        scope: {
          key: cell.preferenceKey,
          expected_revision: cell.expectedRevision
        },
        field: {
          name: 'value',
          title: cell.preferenceKey,
          values: [cell.text || ''],
          class_name: options.length
            ? 'pyasm.widget.input_wdg.SelectWdg'
            : 'pyasm.widget.input_wdg.TextWdg',
          choices: options.map((option) => option.value),
          labels: options.map((option) => option.label)
        }
      };
      await this.$nextTick();
      await this.$refs.inlineEditor.open(anchor.getBoundingClientRect());
    },
    async openCellEditor(record, column, anchor) {
      if (
        !this.columnEditable ||
        this.editBusy ||
        this.editUncertain ||
        !column.editable
      )
        return;
      if (this.cellEditor && !window.confirm(t('Discard unsaved changes?')))
        return;
      const request = ++this.editRequest,
        bounds = anchor.getBoundingClientRect();
      this.$refs.inlineEditor.close();
      this.cellEditor = null;
      this.editError = '';
      this.editBusy = true;
      const context = {
        ticket: this.ticket,
        project: this.project,
        language: 'python'
      };
      const selection =
        this.tableSelection.includes(record.__search_key__) &&
        this.tableSelection.length > 1
          ? this.tableSelection
          : [record.__search_key__];
      try {
        const scope = {
          search_type: this.definition.search_type,
          view: this.table.view || 'table',
          column: column.name,
          search_keys: selection
        };
        const prepared = await this.cellEditCommand(scope);
        if (
          request !== this.editRequest ||
          !anchor.isConnected ||
          Math.abs(anchor.getBoundingClientRect().top - bounds.top) > 1
        )
          return;
        if (
          unsupportedField(prepared.field) ||
          ['ParentInput', 'HiddenWdg', 'FileInput', 'MultiUpload'].includes(
            fieldKind(prepared.field)
          )
        )
          throw new Error('This table cell has no inline editor');
        this.cellEditor = { ...prepared, scope, context };
        this.tableSelect([record], true);
        this.$emit('focus', { kind: 'object', record });
        await this.$nextTick();
        await this.$refs.inlineEditor.open(bounds);
      } catch (error) {
        if (request === this.editRequest) this.columnError = error.message;
      } finally {
        if (request === this.editRequest) this.editBusy = false;
      }
    },
    cancelCellEditor(force = false) {
      if (
        this.editBusy ||
        (this.editUncertain &&
          (!force ||
            !window.confirm(
              t('Discard this draft? Some changes may already have been saved.')
            )))
      )
        return;
      this.editRequest++;
      this.$refs.inlineEditor?.close();
      this.cellEditor = null;
      this.editError = '';
      this.editUncertain = false;
    },
    async saveCellEditor(value, check = false) {
      if (!this.cellEditor || this.editBusy || (this.editUncertain && !check))
        return;
      const request = this.editRequest,
        editor = this.cellEditor,
        field = editor.field;
      if (fieldKind(field) === 'CalendarInputWdg')
        value =
          value === (field.input.value || field.values[0] || '')
            ? field.input.unchanged_value
            : value
              ? value + field.input.value_suffix
              : '';
      if (fieldKind(field) === 'TimeInputWdg')
        value =
          value === field.input.value ? field.input.unchanged_value : value;
      this.editBusy = true;
      this.editError = '';
      try {
        const result = await this.cellEditCommand({
          ...editor.scope,
          action: check ? 'check' : 'save',
          plans: editor.plans,
          value
        });
        if (request !== this.editRequest) return;
        this.editUncertain = check && result.state === 'conflict';
        if (check && result.state !== 'saved') {
          this.editUncertain = true;
          this.editError =
            'Records or definitions changed. Reload before saving.';
          return;
        }
        this.$refs.inlineEditor.close();
        this.cellEditor = null;
        this.editUncertain = false;
        if (result.records?.length) {
          const records = new Map(
            result.records.map((record) => [record.__search_key__, record])
          );
          if (this.ownQuery)
            this.loaded = this.loaded.map(
              (record) => records.get(record.__search_key__) || record
            );
          this.$emit('saved', { records: result.records });
        } else {
          if (this.ownQuery && !editor.preference) await this.load();
          this.$emit('saved');
        }
        await this.loadCells();
      } catch (error) {
        if (request === this.editRequest) {
          this.editError = error.message;
          this.editUncertain = check || !error.status || error.status >= 500;
        }
      } finally {
        if (request === this.editRequest) this.editBusy = false;
      }
    },
    tableSelect(records, value) {
      if (!this.ownQuery) {
        this.$emit('select', records, value);
        return;
      }
      const selected = new Set(this.localSelection);
      for (const record of records)
        if (value) selected.add(record.__search_key__);
        else selected.delete(record.__search_key__);
      this.localSelection = [...selected];
    },
    tableColumn(name, target) {
      this.$emit('column', {
        project: this.project,
        searchType: this.definition.search_type.split('?')[0],
        view:
          target === 'edit_definition'
            ? 'edit_definition'
            : this.table.view || 'table',
        column: name,
        target
      });
    },
    async loadTableConfig() {
      if (
        !this.columnEditable ||
        this.displayedMode !== 'table' ||
        this.tabs ||
        !this.definition?.search_type
      )
        return;
      const request = this.columnRequest;
      try {
        const configuration = await widgetConfiguration(
          'read',
          this.ticket,
          this.project,
          this.definition.search_type,
          this.table.view || 'table'
        );
        if (request === this.columnRequest) this.tableConfig = configuration;
      } catch (error) {
        if (request === this.columnRequest) this.columnError = error.message;
      }
    },
    async selectTableView(view) {
      if (this.columnBusy || this.columnUncertain || !this.canLeave()) return;
      const request = ++this.columnRequest;
      this.columnBusy = true;
      this.columnError = '';
      try {
        const definition = await interfaceDefinition(
          this.ticket,
          this.project,
          this.definition.search_type,
          view
        );
        if (request !== this.columnRequest) return;
        this.tableOverride = definition.table;
        this.tableConfig = null;
        this.tableStateChanged({
          ...this.tableState,
          table: { ...this.tableState.table, view }
        });
      } catch (error) {
        if (request === this.columnRequest) this.columnError = error.message;
      } finally {
        if (request === this.columnRequest) {
          this.columnBusy = false;
          this.loadTableConfig();
        }
      }
    },
    async changeColumns(action, name, value) {
      if (!this.columnEditable) return;
      const request = ++this.columnRequest,
        context = {
          ticket: this.ticket,
          project: this.project,
          type: this.definition.search_type,
          view: this.table.view || 'table'
        };
      this.columnBusy = true;
      this.columnError = '';
      try {
        const configuration =
          this.tableConfig ||
          (await widgetConfiguration(
            'read',
            context.ticket,
            context.project,
            context.type,
            context.view
          ));
        const xml = changeTable(
          tableDefinition(configuration),
          context.view,
          action,
          name,
          value
        );
        if (request !== this.columnRequest) return;
        let destination = configuration,
          target = context.view;
        if (action === 'copy') {
          target = value.view;
          destination = await widgetConfiguration(
            'read',
            context.ticket,
            context.project,
            context.type,
            target
          );
          if (destination.sources.length)
            throw new Error('A table view with this name already exists.');
          if (request !== this.columnRequest) return;
        }
        const saved = await widgetConfiguration(
          'save',
          context.ticket,
          context.project,
          context.type,
          target,
          {
            source_id:
              action === 'copy' ? null : (destination.sources[0]?.id ?? null),
            xml,
            revision: destination.revision
          }
        );
        if (request !== this.columnRequest) return;
        this.tableConfig = saved;
        const definition = await interfaceDefinition(
          context.ticket,
          context.project,
          context.type,
          target
        );
        if (request !== this.columnRequest) return;
        this.tableOverride = definition.table;
        this.tableStateChanged({
          ...this.tableState,
          table: { ...this.tableState.table, view: target }
        });
      } catch (error) {
        if (request === this.columnRequest) {
          this.columnError = error.message;
          this.columnUncertain = !error.status || error.status >= 500;
        }
      } finally {
        if (request === this.columnRequest) this.columnBusy = false;
      }
    },
    saveTableView(title) {
      title = title.normalize('NFKC').trim();
      const slug = title
        .replace(/[^\p{L}\p{N}_]+/gu, '_')
        .replace(/^_+|_+$/g, '')
        .toLocaleLowerCase()
        .slice(0, 55);
      if (!slug) {
        this.columnError = 'Table view name requires letters or numbers.';
        return;
      }
      this.changeColumns('copy', '', { view: 'th_table_' + slug, title });
    },
    async openTableRecordForm(records, sourceKey = null, operation = '') {
      if (this.readOnly || !this.targetRecord) return;
      await this.$nextTick();
      this.$refs.tableForm.open(
        Array.isArray(records)
          ? records.map((record) => record.__search_key__)
          : records?.__search_key__ || null,
        sourceKey,
        { operation }
      );
    },
    async openTableRelations(record) {
      const request = this.actionRequest;
      try {
        await RelatedObjects.__asyncLoader();
        if (request !== this.actionRequest) return;
        this.relatedVisited = true;
        await this.$nextTick();
        if (request === this.actionRequest)
          this.$refs.tableRelated.open(record);
      } catch (error) {
        if (request === this.actionRequest) this.columnError = error.message;
      }
    },
    async openNestedEditor(record, state) {
      if (this.readOnly) return;
      const form = this.$refs.nestedForm;
      const uploads = Object.values(form?.files || {}).some((value) =>
        Array.isArray(value) ? value.length : !!value
      );
      if (
        form?.$refs?.dialog?.open &&
        (form.loading ||
          form.saving ||
          form.dirty ||
          uploads ||
          form.uncertain ||
          form.createBatch)
      ) {
        form.$refs.dialog.show();
        return;
      }
      this.nestedEditor = state;
      await this.$nextTick();
      this.$refs.nestedForm.open(
        record?.__search_key__ || null,
        null,
        record?.__search_key__ ||
          state.scope.projectScope ||
          state.scope.searchType === state.scope.parentKey.split('?')[0]
          ? {}
          : { parent_key: state.scope.parentKey }
      );
    },
    nestedCellEvent(name, record, values) {
      if (name === 'preview') this.$refs.preview.open(record, ...values);
      else if (name === 'notes') this.$refs.notes.open(record, ...values);
      else if (name === 'tasks') this.$refs.notes.openTask(record, ...values);
      else if (name === 'task-edit') this.openTaskEditor(record, ...values);
    },
    async tableSaved() {
      const pending = Object.values(this.expandedTables);
      while (pending.length) {
        const state = pending.pop();
        state.revision = (state.revision || 0) + 1;
        pending.push(...Object.values(state.children || {}));
      }
      if (this.ownQuery) await this.load();
      await this.loadCells();
      this.$emit('saved');
    },
    async tableHeaderAction(action) {
      if (this.readOnly || this.serviceBusy) return;
      this.targetRecord = {
        __search_key__:
          this.definition.search_type +
          '?project=' +
          encodeURIComponent(this.project)
      };
      this.targetInsertView = action.view;
      await this.$nextTick();
      this.$refs.tableForm.open(null, null, {
        operation: action.type === 'publish' ? 'publish' : ''
      });
    },
    async createParentChild(cell) {
      if (this.readOnly || !cell.parent || cell.parent.retired) return;
      this.targetRecord = {
        __search_key__:
          cell.targetSearchKey.split('?')[0] +
          '?project=' +
          encodeURIComponent(cell.projectCode || this.project)
      };
      this.targetInsertView = 'insert';
      this.targetIgnore = [];
      await this.$nextTick();
      this.$refs.tableForm.open(null, null, {
        parent_key: cell.parent.searchKey
      });
    },
    async openCustomLayout(model, title = '', tabKey = '', record = null) {
      const request = ++this.documentRequest;
      this.serviceDocument = {
        ...model,
        title: title || model.title || 'Custom Layout',
        translateTitle: !title,
        tabKey,
        record: record || model.layoutRecord
      };
      await this.$nextTick();
      if (request === this.documentRequest) this.$refs.tableDocument.open();
    },
    async runConfiguredScript(record, cell, context, request) {
      this.serviceBusy = true;
      const abort = new AbortController();
      this.scriptAbort = abort;
      let source =
        cell.displayOptions?.cbjs_action || cell.displayOptions?.javascript;
      if (!source && cell.scriptKey) {
        const saved = await rpc('get_by_search_key', [context, cell.scriptKey]);
        if (!saved) throw new Error('Script is no longer available');
        if (
          !['javascript', 'js'].includes(
            String(saved.language || 'javascript').toLowerCase()
          )
        )
          throw new Error('Table button scripts must use JavaScript');
        source = saved.script;
      }
      if (!source) throw new Error('No script defined for this button');
      if (request !== this.actionRequest) return;
      const targetKey = cell.targetSearchKey || record.__search_key__;
      const selectedKeys = [
        ...(cell.tableScope?.searchKeys || this.tableSelection)
      ];
      const result = await runTableScript(
        source,
        {
          searchKey: targetKey,
          searchType: targetKey.split('?')[0],
          project: context.project,
          column: cell.columnName,
          view:
            cell.layoutView ||
            cell.tableScope?.view ||
            this.table.view ||
            'table',
          record: { ...record },
          searchKeys: selectedKeys,
          records:
            cell.tableScope?.records ||
            Object.fromEntries(
              this.records
                .filter((row) => selectedKeys.includes(row.__search_key__))
                .map((row) => [row.__search_key__, { code: row.code }])
            )
        },
        {
          ticket: context.ticket,
          signal: abort.signal,
          confirm: (message) =>
            this.$refs.tableServiceDialogs.ask(message, {
              width: 480,
              height: 220
            }),
          progress: (title, detail) => {
            if (request === this.actionRequest)
              this.serviceMessage = [title, detail].filter(Boolean).join(' ');
          }
        }
      );
      if (request !== this.actionRequest) return;
      const ports = result.commands.map(tableActionRoute);
      for (const command of ports) {
        if (request !== this.actionRequest) return;
        const options = command.options || {};
        if (command.type === 'refresh') await this.tableSaved();
        else if (['message', 'log'].includes(command.type))
          this.serviceMessage = command.text;
        else if (command.type === 'url') {
          const href = tableLink(command.url, location.origin);
          if (!href) throw new Error('Unsupported table link');
          window.open(href, '_blank', 'noopener,noreferrer');
        } else if (command.type === 'edit') {
          const key = options.search_key;
          const searchType = options.search_type || key?.split('?')[0];
          if (!searchType)
            throw new Error('Search Type is not available for this editor');
          this.targetRecord = key
            ? await rpc('get_by_search_key', [context, key])
            : {
                __search_key__:
                  searchType + '?project=' + encodeURIComponent(context.project)
              };
          if (!this.targetRecord || request !== this.actionRequest) return;
          this.targetIgnore = String(options.ignore || '')
            .split('|')
            .filter(Boolean);
          this.targetEditView = options.view || 'edit';
          this.targetInsertView = options.view || 'insert';
          await this.$nextTick();
          this.$refs.tableForm.open(key || null);
        } else if (command.type === 'notes') {
          const target =
            options.search_key === record.__search_key__
              ? record
              : await rpc('get_by_search_key', [context, options.search_key]);
          if (request === this.actionRequest && target)
            await this.$refs.notes.open(
              target,
              { targetSearchKey: target.__search_key__ },
              options.process || options.context || 'publish'
            );
        } else if (
          ['security-summary', 'custom-layout'].includes(command.type)
        ) {
          const documentRequest = ++this.documentRequest;
          const result = await rpc('execute_cmd', [
            context,
            command.type === 'security-summary'
              ? 'tactic.ui.table.TableDocumentReadCmd'
              : 'tactic.ui.table.CustomLayoutReadCmd',
            command.type === 'security-summary'
              ? { search_key: options.search_key }
              : {
                  search_key: options.search_key || record.__search_key__,
                  view: options.view || ''
                }
          ]);
          if (
            request !== this.actionRequest ||
            documentRequest !== this.documentRequest
          )
            return;
          await this.openCustomLayout(
            result.info,
            command.title,
            command.tabKey || '',
            record
          );
        } else if (this.openTablePort)
          await this.openTablePort(command, record);
        else throw new Error('Unsupported table window: ' + command.type);
      }
      if (this.scriptAbort === abort) this.scriptAbort = null;
    },
    async tableAction(record, kind, cell, anchor) {
      if (
        this.serviceBusy ||
        (this.readOnly &&
          [
            'edit',
            'retire',
            'reactivate',
            'delete',
            'checkin',
            'file-append',
            'remove-connection',
            'template',
            'preference',
            'notification-test',
            'script',
            'edit-links',
            'drop-links',
            'file-ingest',
            'change-parent',
            'drop-parent',
            'publish',
            'add-task',
            'work'
          ].includes(kind)) ||
        cell?.available === false
      )
        return;
      const request = ++this.actionRequest,
        context = {
          ticket: this.ticket,
          project: cell.tableScope?.projectCode || this.project,
          language: 'python'
        };
      this.columnError = '';
      this.serviceMessage = '';
      try {
        if (kind === 'error') throw new Error(cell.error);
        if (kind === 'change-parent' || kind === 'drop-parent') {
          await this.$refs.parentPicker.open(
            cell,
            record.name || record.title || record.code || '',
            anchor
          );
          return;
        }
        if (kind === 'remove-connection') {
          if (
            !(await this.$refs.tableServiceDialogs.ask(
              t('Remove this connection? The connected objects will be kept.'),
              {
                accept: 'Remove connection',
                destructive: true
              }
            )) ||
            request !== this.actionRequest
          )
            return;
          this.serviceBusy = true;
          try {
            await rpc('execute_cmd', [
              context,
              'tactic.ui.table.connections.TableConnectionRemoveCmd',
              {
                parent_key: cell.targetSearchKey || record.__search_key__,
                connection_key: cell.connectionKey,
                expected_revision: cell.expectedRevision,
                direction: cell.direction || 'dst'
              }
            ]);
          } finally {
            if (request === this.actionRequest) await this.loadCells();
          }
          return;
        }
        if (kind === 'file-ingest') {
          let files = Array.isArray(cell.dropFiles) ? cell.dropFiles : [];
          if (!files.length) {
            files = await new Promise((resolve) => {
              const input = document.createElement('input');
              input.type = 'file';
              input.multiple = true;
              input.onchange = () => resolve(Array.from(input.files || []));
              input.oncancel = () => resolve([]);
              input.click();
            });
          }
          if (!files.length || request !== this.actionRequest) return;
          this.serviceBusy = true;
          const project =
            cell.projectCode || record.project_code || context.project;
          const uploadDirectory =
            'ingest_' + Date.now() + '_' + Math.random().toString(16).slice(2);
          const names = [];
          for (const file of files) {
            names.push(
              await uploadFormFile(context.ticket, project, file, {
                subdir: uploadDirectory
              })
            );
            if (request !== this.actionRequest) return;
          }
          const result = await rpc('execute_cmd', [
            { ...context, project },
            'tactic.ui.widget.file_browser_wdg.FileIngestCmd',
            {
              search_key: cell.targetSearchKey || record.__search_key__,
              files: names,
              upload_directory: uploadDirectory,
              transfer_mode: cell.transferMode || 'free_copy',
              checkin_mode: cell.checkinMode || 'default',
              context: cell.context || 'publish',
              subcontext_mode: cell.subcontextMode || '{none}',
              subcontext: cell.subcontext || ''
            }
          ]);
          if (request === this.actionRequest) {
            this.serviceMessage = result.description || '';
            await this.tableSaved();
          }
          return;
        }
        if (kind === 'file-checkout') {
          if (cell.requiresDesktop)
            throw new Error('This checkout mode requires a desktop connection');
          this.checkoutProject =
            cell.projectCode || record.project_code || this.project;
          await SnapshotCheckout.__asyncLoader();
          if (request !== this.actionRequest) return;
          this.checkoutVisited = true;
          await this.$nextTick();
          await this.$refs.tableCheckout.open({
            ...record,
            __search_key__: cell.targetSearchKey || record.__search_key__
          });
          return;
        }
        if (kind === 'layout-document') {
          await this.openCustomLayout(cell, cell.layoutView || '', '', record);
          return;
        }
        if (kind === 'nested-table') {
          const key = record.__search_key__,
            previous = this.expandedTables[key];
          if (
            previous &&
            previous.column === cell.columnName &&
            JSON.stringify(previous.scope) === JSON.stringify(cell.nestedTable)
          )
            previous.open = !previous.open;
          else
            this.expandedTables[key] = {
              scope: cell.nestedTable,
              column: cell.columnName,
              open: true,
              selected: [],
              offset: 0,
              rows: [],
              columns: [],
              selection: cell.nestedTable.selection
            };
          return;
        }
        if (kind === 'layout-link') {
          const href = tableLink(cell.href, location.origin);
          if (!href) throw new Error('Unsupported table link');
          window.open(href, '_blank', 'noopener,noreferrer');
          return;
        }
        if (kind === 'script') {
          const scriptRecord =
            cell.targetSearchKey &&
            cell.targetSearchKey !== record.__search_key__
              ? await rpc('get_by_search_key', [context, cell.targetSearchKey])
              : record;
          if (request !== this.actionRequest) return;
          if (!scriptRecord)
            throw new Error('The configured table target is unavailable');
          await this.runConfiguredScript(scriptRecord, cell, context, request);
          return;
        }
        if (kind === 'preference') {
          await this.openPreference(record, cell, anchor);
          return;
        }
        if (kind === 'security') {
          if (this.openTableSecurity)
            await this.openTableSecurity(cell.groupCode);
          else
            throw new Error('Global Permissions are unavailable in this host');
          return;
        }
        if (kind === 'template') {
          this.serviceBusy = true;
          if (
            !(await this.$refs.tableServiceDialogs.ask(
              t('Update the template archive for {project}?').replace(
                '{project}',
                cell.projectCode
              )
            ))
          )
            return;
          if (request !== this.actionRequest) return;
          await rpc('execute_cmd', [
            { ...context, project: 'admin' },
            'tactic.command.ProjectTemplateCreatorCmd',
            { project_code: cell.projectCode }
          ]);
          if (request === this.actionRequest)
            this.serviceMessage = t('Template archive created');
          return;
        }
        // shortcut: browsers copy native local paths; opening folders needs the desktop bridge.
        if (kind === 'explorer') {
          await copyText(cell?.path || '');
          this.columnError =
            'Opening local folders requires a desktop connection. The TACTIC path was copied.';
          return;
        }
        const key = cell?.targetSearchKey || record.__search_key__;
        const targetContext = {
          ...context,
          project:
            (kind === 'file-append' && cell.projectCode) ||
            cell.tableScope?.projectCode ||
            new URL('skey://' + key).searchParams.get('project') ||
            context.project
        };
        if (kind === 'dependencies') {
          this.documentRequest++;
          const sourceProject = cell.projectCode || targetContext.project;
          this.serviceDocument = {
            kind: 'dependencies',
            title: 'Dependencies',
            searchKey: key,
            projectCode: sourceProject,
            context: { ...targetContext, project: sourceProject },
            record
          };
          await this.$nextTick();
          if (request === this.actionRequest) this.$refs.tableDocument.open();
          return;
        }
        const target =
          key === record.__search_key__ && kind !== 'notification-test'
            ? record
            : await rpc('get_by_search_key', [targetContext, key]);
        if (request !== this.actionRequest) return;
        if (['retire', 'reactivate'].includes(kind) && cell.expectedRevision) {
          this.serviceBusy = true;
          const message =
            kind === 'retire'
              ? 'Retire this object?'
              : 'Reactivate this object?';
          if (
            !(await this.$refs.tableServiceDialogs.ask(t(message), {
              accept: kind === 'retire' ? 'Retire' : 'Reactivate',
              destructive: kind === 'retire'
            }))
          )
            return;
          if (request !== this.actionRequest) return;
          await rpc('execute_cmd', [
            targetContext,
            'tactic.ui.table.TableObjectStatusCmd',
            {
              search_key: key,
              action: kind,
              expected_revision: cell.expectedRevision
            }
          ]);
          if (request === this.actionRequest) await this.tableSaved();
          return;
        }
        if (['edit-links', 'drop-links'].includes(kind)) {
          const related = this.$refs.tableRelated;
          if (
            related?.$refs?.dialog?.open &&
            (related.dirty ||
              related.saving ||
              related.busy ||
              related.availableBusy ||
              related.uncertain)
          )
            throw new Error('Apply or discard unsaved changes first');
          await RelatedObjects.__asyncLoader();
          if (request !== this.actionRequest) return;
          this.relatedVisited = true;
          this.targetProject = targetContext.project;
          this.targetRecord = target;
          await this.$nextTick();
          if (request !== this.actionRequest) return;
          await this.$refs.tableRelated.openDrop(target, {
            ...cell,
            tableView:
              cell.tableView ||
              cell.tableScope?.view ||
              this.table.view ||
              'table'
          });
          if (request === this.actionRequest && kind === 'drop-links')
            await this.$refs.tableRelated.stageDropped(cell.dropKeys);
          return;
        }
        if (
          [
            'task-details',
            'add-task',
            'work',
            'table-schedule',
            'work-hours'
          ].includes(kind)
        ) {
          if (!this.openTablePort)
            throw new Error('Unsupported table window: ' + kind);
          await this.openTablePort({ type: kind, options: cell }, target);
          return;
        }
        if (kind === 'notification-test') {
          this.serviceBusy = true;
          const result = await rpc('execute_cmd', [
            targetContext,
            'tactic.command.NotificationTestCmd',
            { sobject_dict: target }
          ]);
          if (request === this.actionRequest)
            this.serviceMessage = result.description || '';
          return;
        }
        if (['sobject_detail', 'file_list', 'metadata'].includes(kind)) {
          this.$emit('inspect', target);
          return;
        }
        const definition = await interfaceDefinition(
          context.ticket,
          targetContext.project,
          key.split('?')[0],
          'table'
        );
        if (request !== this.actionRequest) return;
        if (
          ['checkin', 'file-append'].includes(kind) &&
          !definition.operations.checkin
        )
          throw new Error(
            'This operation or object type is not available yet.'
          );
        if (kind === 'checkin' && this.openTableCheckin && !this.mobile) {
          await this.openTableCheckin(target, cell, targetContext.project);
          return;
        }
        this.targetOperations = definition.operations;
        this.targetRecord =
          kind === 'file-append'
            ? { ...target, project_code: targetContext.project }
            : target;
        await this.$nextTick();
        if (['delete', 'retire', 'reactivate'].includes(kind))
          this.$refs.tableDelete.open(target, kind);
        else if (kind === 'edit' || kind === 'publish') {
          this.targetIgnore = [];
          this.targetEditView =
            cell.actionView ||
            cell.publishView ||
            (kind === 'publish' ? 'publish' : 'edit');
          await this.openTableRecordForm(
            target,
            null,
            kind === 'publish' ? 'publish' : ''
          );
        } else if (kind === 'checkin' || kind === 'file-append')
          await this.$refs.tableOperations.quick(
            target,
            {
              branch: {
                kind: 'process',
                process: cell.process,
                context: cell.context
              }
            },
            kind === 'file-append' ? 'append' : 'save',
            {
              process: cell.process,
              context: cell.context,
              checkinType: cell.checkinMode,
              transferMode: cell.transferMode
            }
          );
      } catch (error) {
        if (request === this.actionRequest) this.columnError = error.message;
      } finally {
        if (request === this.actionRequest) {
          this.serviceBusy = false;
          this.scriptAbort = null;
        }
      }
    },
    beforeUnload(event) {
      if (
        this.serviceBusy ||
        this.dirtyTaskCount ||
        this.taskBusy ||
        this.taskUncertain ||
        this.cellEditor ||
        this.editBusy ||
        this.editUncertain ||
        this.columnBusy ||
        this.columnUncertain
      ) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    canLeave() {
      if (
        this.serviceBusy ||
        this.editBusy ||
        this.columnBusy ||
        this.columnUncertain
      )
        return false;
      if (this.cellEditor && !window.confirm(t('Discard unsaved changes?')))
        return false;
      this.cancelCellEditor(true);
      if (this.taskBusy) return false;
      if (
        (this.dirtyTaskCount || this.taskUncertain) &&
        !window.confirm(t('Discard unsaved task changes?'))
      )
        return false;
      this.taskDrafts = {};
      this.taskUncertain = false;
      this.$refs.taskEditor?.close();
      return true;
    },
    async taskCommand(values) {
      if (
        this.taskContext &&
        (this.taskContext.ticket !== this.ticket ||
          this.taskContext.project !== this.project)
      ) {
        const error = new Error(
          'Connection context changed. Close this form and reopen it before saving.'
        );
        error.status = 400;
        throw error;
      }
      return (
        await rpc('execute_cmd', [
          this.taskContext || { ticket: this.ticket, project: this.project },
          'tactic.ui.table.task_inspector.TaskTableEditCmd',
          values
        ])
      ).info;
    },
    taskDraftKey(plan) {
      return JSON.stringify([plan.search_key, plan.task_key, plan.context]);
    },
    async openTaskEditor(record, cell, task, field, bounds) {
      if (this.readOnly || this.taskBusy || this.taskUncertain || !task) return;
      const request = ++this.taskRequest;
      this.taskBusy = true;
      this.taskError = '';
      this.taskEditor = null;
      if (!this.dirtyTaskCount)
        this.taskContext = { ticket: this.ticket, project: this.project };
      try {
        const result = await this.taskCommand({
          source: {
            search_key: record.__search_key__,
            task_key: task.taskSearchKey || '',
            process: task.process,
            context: task.context || task.process
          },
          search_keys:
            this.tableSelection.includes(record.__search_key__) &&
            this.tableSelection.length > 1
              ? this.tableSelection
              : [record.__search_key__]
        });
        if (
          request !== this.taskRequest ||
          !this.$el.offsetParent ||
          (bounds.anchor &&
            (!bounds.anchor.isConnected ||
              Math.abs(bounds.anchor.getBoundingClientRect().top - bounds.top) >
                1))
        )
          return;
        for (const plan of result.plans) {
          const draft = this.taskDrafts[this.taskDraftKey(plan)];
          if (draft && draft.plan.expected_revision !== plan.expected_revision)
            throw new Error('Tasks changed. Reload before saving.');
        }
        const first =
          result.plans.find(
            (plan) => plan.search_key === record.__search_key__
          ) || result.plans[0];
        const draft = this.taskDrafts[this.taskDraftKey(first)];
        const names = field.endsWith('_date')
          ? ['bid_start_date', 'bid_end_date']
          : [field];
        this.taskEditor = {
          plans: result.plans,
          process: task.process,
          fields: first.fields
            .filter((item) => names.includes(item.name))
            .map((item) => ({
              ...item,
              editable: result.plans.every((plan) =>
                plan.fields.some(
                  (field) => field.name === item.name && field.editable
                )
              )
            })),
          statuses: first.statuses.filter((value) =>
            result.plans.every((plan) => plan.statuses.includes(value))
          ),
          users: first.users.filter((user) =>
            result.plans.every((plan) =>
              plan.users.some((item) => item.value === user.value)
            )
          ),
          values: { ...first.task, ...draft?.data }
        };
        this.taskBusy = false;
        await this.$refs.taskEditor.open(bounds);
      } catch (error) {
        if (request === this.taskRequest) this.taskError = error.message;
      } finally {
        if (request === this.taskRequest) this.taskBusy = false;
      }
    },
    stageTask(name, value) {
      if (this.taskBusy || !this.taskEditor || this.taskUncertain) return;
      const editor = this.taskEditor;
      if (!editor.fields.some((field) => field.name === name && field.editable))
        return;
      if (
        (name === 'status' && !editor.statuses.includes(value)) ||
        (name === 'assigned' &&
          value &&
          !editor.users.some((user) => user.value === value))
      )
        return;
      for (const plan of editor.plans) {
        const key = this.taskDraftKey(plan);
        const draft = this.taskDrafts[key] || { plan, data: {} };
        const normal = (value) =>
          name.endsWith('_date')
            ? String(value || '')
                .replace('T', ' ')
                .slice(0, 16)
            : String(value || '');
        if (normal(value) === normal(draft.plan.task[name]))
          delete draft.data[name];
        else draft.data[name] = value;
        if (Object.keys(draft.data).length) this.taskDrafts[key] = draft;
        else delete this.taskDrafts[key];
      }
      editor.values[name] = value;
      if (['status', 'assigned'].includes(name)) this.$refs.taskEditor.close();
    },
    async discardTasks() {
      if (
        this.taskBusy ||
        (this.taskUncertain &&
          !window.confirm(
            t('Discard this draft? Some changes may already have been saved.')
          ))
      )
        return;
      this.$refs.taskEditor.close();
      this.taskDrafts = {};
      this.taskError = '';
      this.taskUncertain = false;
      this.taskContext = null;
      await this.loadCells();
    },
    async saveTasks(check = false) {
      if (
        this.taskBusy ||
        !this.dirtyTaskCount ||
        (this.taskUncertain && !check)
      )
        return;
      this.$refs.taskEditor.close();
      this.taskBusy = true;
      this.taskError = '';
      const request = ++this.taskRequest;
      try {
        const result = await this.taskCommand({
          action: check ? 'check' : 'save',
          plans: Object.values(this.taskDrafts).map((draft) => ({
            search_key: draft.plan.search_key,
            task_key: draft.plan.task_key,
            process: draft.plan.process,
            context: draft.plan.context,
            expected_revision: draft.plan.expected_revision,
            data: draft.data
          }))
        });
        if (request !== this.taskRequest) return;
        if (!check || result.state === 'saved') this.taskDrafts = {};
        this.taskUncertain = check && result.state === 'conflict';
        if (this.taskUncertain)
          this.taskError = 'Tasks changed. Reload before saving.';
        await this.loadCells();
      } catch (error) {
        if (request === this.taskRequest) {
          this.taskError = error.message;
          this.taskUncertain = check || !error.status || error.status >= 500;
        }
      } finally {
        if (request === this.taskRequest) this.taskBusy = false;
      }
    },
    async loadCells(previous) {
      if (this.displayedMode !== 'table') return;
      const append =
        Array.isArray(previous?.[0]) &&
        previous[0].length < this.records.length &&
        previous[0].every((record, index) => record === this.records[index]) &&
        previous
          .slice(1)
          .every((value, index) => value === this.cellContext[index + 1]);
      if (!append) {
        this.$refs.taskEditor?.close();
        const sameContext =
          !Array.isArray(previous) ||
          previous
            .slice(1)
            .every((value, index) => value === this.cellContext[index + 1]);
        const keys = new Set(
          this.records.map((record) => record.__search_key__)
        );
        this.cells = sameContext
          ? Object.fromEntries(
              Object.entries(this.cells).filter(([key]) => keys.has(key))
            )
          : {};
        this.expandedDetails = {};
      }
      const request = ++this.cellRequest;
      this.cellError = '';
      this.cellsBusy = false;
      if (
        !this.records.length ||
        !this.elements.some((element) => element.cell?.server)
      )
        return;
      const records = append
        ? this.records.filter(
            (record) => !(record.__search_key__ in this.cells)
          )
        : this.records;
      if (!records.length) return;
      this.cellsBusy = true;
      try {
        for (let start = 0; start < records.length; start += 500) {
          if (request !== this.cellRequest) return;
          const cells = await tableCells(
            this.ticket,
            this.project,
            this.definition.search_type,
            this.table.view || 'table',
            records
              .slice(start, start + 500)
              .map((record) => record.__search_key__)
          );
          if (request === this.cellRequest)
            this.cells = { ...this.cells, ...cells };
        }
      } catch (error) {
        if (request === this.cellRequest) this.cellError = error.message;
      } finally {
        if (request === this.cellRequest) this.cellsBusy = false;
      }
    },
    async operate(record, event) {
      if (this.readOnly) return;
      event.preventDefault();
      if (this.ownQuery) {
        this.targetRecord = record;
        this.targetOperations = this.definition.operations;
        await this.$nextTick();
        this.$refs.tableOperations.open(record, event);
      } else this.$emit('operate', record, event);
    },
    reset() {
      this.page = 0;
      this.pageSize = this.definition?.panel?.search_limit || 50;
      this.filterField = this.columnNames.includes('name')
        ? 'name'
        : this.columnNames.includes('code')
          ? 'code'
          : this.columnNames[0] || '';
      this.filterValue = '';
      this.filters = [];
      this.localSortField = '';
      this.localSortDirection = 'asc';
      this.load(this.definition?.panel?.do_initial_search !== false);
    },
    applyFilter() {
      const value = this.filterValue.trim();
      const dataType =
        this.definition?.columns[this.filterField]?.data_type || '';
      this.filters =
        value && this.filterField
          ? [
              [
                this.filterField,
                /^(?:text|varchar|char|nvarchar|nchar|character varying|citext)/i.test(
                  dataType
                )
                  ? 'contains'
                  : '=',
                value
              ]
            ]
          : [];
      this.page = 0;
      this.load();
    },
    sortBy(field, direction) {
      if (!this.ownQuery) {
        this.$emit('sort', field, direction);
        return;
      }
      this.localSortDirection =
        direction ||
        (this.activeSortField === field && this.activeSortDirection === 'asc'
          ? 'desc'
          : 'asc');
      this.localSortField = field;
      this.page = 0;
      this.load();
    },
    changePage(direction) {
      this.page += direction;
      this.load();
    },
    changePageSize() {
      this.page = 0;
      this.load();
    },
    async load(start = true) {
      const id = ++this.request;
      this.loaded = [];
      this.error = '';
      this.busy = this.hasNext = false;
      this.started = start;
      if (!start || !this.ownQuery || !this.definition?.search_type) return;
      this.busy = true;
      try {
        const order = this.definition.panel?.order_by || [];
        const rows = await rpc(
          'query',
          [
            { ticket: this.ticket, project: this.project, language: 'python' },
            this.definition.search_type
          ],
          {
            filters: this.filters,
            limit: this.pageSize + 1,
            offset: this.page * this.pageSize,
            parent_key: this.parentKey || null,
            order_bys: this.localSortField
              ? [`${this.localSortField} ${this.localSortDirection}`, ...order]
              : order
          }
        );
        if (id === this.request) {
          this.loaded = rows.slice(0, this.pageSize);
          this.hasNext = rows.length > this.pageSize;
        }
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    moveTab(event) {
      const names = this.table.elements.map((item) => item.name);
      let index = names.indexOf(this.selected);
      if (event.key === 'ArrowRight') index = (index + 1) % names.length;
      else if (event.key === 'ArrowLeft')
        index = (index + names.length - 1) % names.length;
      else if (event.key === 'Home') index = 0;
      else if (event.key === 'End') index = names.length - 1;
      else return;
      event.preventDefault();
      this.selected = names[index];
      this.$nextTick(() =>
        this.$refs.tabs.querySelector('[aria-selected="true"]').focus()
      );
    }
  }
};
</script>

<template>
  <div
    class="configured-view"
    :data-result-mode="displayedMode"
    :aria-busy="busy || cellsBusy"
  >
    <CustomLayoutView
      v-if="layoutModel"
      :model="layoutModel"
      :filter-busy="layoutBusy"
      @filter-apply="$emit('filter-apply', $event)"
      :ticket="ticket"
      :project="project"
      :width="layoutWidth"
      :height="layoutHeight"
      :selected-keys="selectedKeys"
      :workspace-id="workspaceId"
      :active="active"
      @loaded="$emit('loaded', $event)"
      @action="tableAction"
      @edit="openNestedEditor"
      @inspect="$emit('inspect', $event)"
      @operate="(...args) => $emit('operate', ...args)"
      @select="(...args) => $emit('select', ...args)"
      @focus="$emit('focus', $event)"
      @cell-event="nestedCellEvent"
      @column="$emit('column', $event)"
      @saved="tableSaved"
      @notice="serviceMessage = $event"
      @close="$emit('close')"
    />
    <template v-else-if="tabs">
      <div
        ref="tabs"
        class="view-tabs"
        role="tablist"
        :aria-label="table.view"
        @keydown="moveTab"
      >
        <button
          v-for="(item, index) in table.elements"
          :id="`${tabId}-tab-${index}`"
          :key="item.name"
          role="tab"
          :aria-selected="selected === item.name"
          :tabindex="selected === item.name ? 0 : -1"
          :aria-controls="`${tabId}-panel-${index}`"
          @click="selected = item.name"
        >
          {{ item.title }}
        </button>
      </div>
      <section
        v-for="(item, index) in table.elements"
        v-show="selected === item.name"
        :id="`${tabId}-panel-${index}`"
        :key="item.name"
        role="tabpanel"
        :aria-labelledby="`${tabId}-tab-${index}`"
        tabindex="0"
      >
        <KeepAlive
          ><ConfiguredView
            v-if="selected === item.name && item.interface"
            :key="item.name"
            :definition="item.interface"
            :ticket="ticket"
            :project="project"
            :parent-key="parentKey"
            :read-only="readOnly"
            :accent="accent"
            @inspect="$emit('inspect', $event)"
            @operate="
              (record, event, node) => $emit('operate', record, event, node)
            "
            @column="$emit('column', $event)"
            @saved="$emit('saved')"
        /></KeepAlive>
        <p v-if="selected === item.name && !item.interface" class="notice">
          {{ t('This widget is not available yet.') }}
          {{ item.display.handler }}
        </p>
      </section>
      <p v-if="!table.elements.length" class="table-message">
        {{ t('This view has no elements.') }}
      </p>
    </template>
    <template v-else>
      <form
        v-if="ownQuery"
        class="toolbar panel-toolbar"
        :aria-label="t('View search')"
        @submit.prevent="applyFilter"
      >
        <AppSearchField
          v-model="filterValue"
          label="Filter value"
          :placeholder="t('Filter value')"
          :disabled="busy"
        />
        <AppButton
          type="submit"
          label="Find"
          icon="search"
          highlighted
          :icon-only="mobile"
          :disabled="busy || !filterField"
        />
        <component
          :is="mobile ? 'AppMenu' : 'div'"
          class="panel-search-options"
          label="View search options"
          :overlay="mobile"
          :close-on-select="false"
        >
          <AppSelect
            v-model="filterField"
            label="Filter field"
            :translate-labels="false"
            :disabled="busy || !columnNames.length"
            :options="columnNames.map((name) => ({ value: name, label: name }))"
          />
          <label
            v-if="definition.panel?.show_search_limit !== false"
            class="panel-page-limit"
            >{{ t('Records per page')
            }}<AppSelect
              v-model="pageSize"
              label="Records per page"
              :disabled="busy"
              :options="
                pageSizes.map((size) => ({ value: size, label: String(size) }))
              "
              @update:model-value="changePageSize"
          /></label>
          <AppButton
            v-if="definition.panel?.show_refresh !== false"
            class="panel-refresh"
            label="Refresh"
            icon="refresh"
            :disabled="busy"
            @click="load()"
          />
        </component>
      </form>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <p v-if="columnError" class="error" role="alert">{{ t(columnError) }}</p>
      <p v-if="columnError" class="notice">
        <span v-if="columnUncertain">{{
          t('Check the server result before saving again.')
        }}</span
        ><AppButton
          label="Reload from server"
          icon="refresh"
          @click="
            columnUncertain = false;
            tableConfig = null;
            selectTableView(table.view || 'table');
          "
        />
      </p>
      <p v-if="cellError" class="error" role="alert">{{ t(cellError) }}</p>
      <p v-if="taskError" class="error" role="alert">{{ t(taskError) }}</p>
      <p v-if="taskUncertain" class="notice">
        {{ t('Check the server result before saving again.') }}
      </p>
      <div
        v-if="dirtyTaskCount"
        class="task-draft-actions"
        role="region"
        :aria-label="t('Pending task changes')"
      >
        <span role="status">{{
          t('{count} unsaved tasks', { count: dirtyTaskCount })
        }}</span>
        <AppButton
          label="Discard task changes"
          icon="undo"
          icon-only
          :disabled="taskBusy"
          @click="discardTasks"
        />
        <AppButton
          v-if="taskUncertain"
          label="Check saved task changes"
          icon="refresh"
          icon-only
          :disabled="taskBusy"
          @click="saveTasks(true)"
        />
        <AppButton
          label="Save task changes"
          icon="save"
          icon-only
          highlighted
          :disabled="taskBusy || taskUncertain"
          @click="saveTasks()"
        />
      </div>
      <div v-if="busy" class="table-message" role="status">
        {{ t('Loading data…') }}
      </div>
      <div v-else-if="!supportedLayout" class="table-message">
        {{ t('This layout is not available yet.') }}
      </div>
      <ResultPresentation
        @organization="$emit('organization', $event)"
        ref="presentation"
        v-if="(rows !== null || table.item_layout) && !tabs"
        v-show="displayedMode !== 'table'"
        :active="displayedMode !== 'table'"
        :item-layout="itemLayout"
        :read-only="readOnly"
        :rows="records"
        :ticket="ticket"
        :project="project"
        :search-type="definition.search_type"
        :mode="displayedMode"
        :workspace-id="workspaceId"
        @root-scroll="$emit('result-scroll', $event)"
        @focus="$emit('focus', $event)"
        :group-mode="groupMode"
        :state="resultState"
        @state="$emit('result-state', $event)"
        :selected-keys="selectedKeys"
        @inspect="$emit('inspect', $event)"
        @select="(rows, selected) => $emit('select', rows, selected)"
        @operate="
          (record, event, node) => $emit('operate', record, event, node)
        "
      />
      <template v-if="!busy && supportedLayout && displayedMode === 'table'">
        <p v-if="elements.some((item) => !item.supported)" class="notice">
          {{ t('Some widgets in this view are not available yet.') }}
        </p>
        <div v-if="!elements.length" class="table-message">
          {{ t('This view has no elements.') }}
        </div>
        <TableView
          v-else
          ref="tableView"
          :columns="elements"
          :groups="rowGroups"
          :selected-keys="tableSelection"
          :selectable="selectable"
          :read-only="readOnly"
          :editable="columnEditable"
          :busy="columnBusy || editBusy || taskBusy"
          :accent="accent"
          :state="tableState"
          :views="tableViews"
          :closed-groups="closedGroups"
          :expanded-rows="expandedTables"
          :cells="displayCells"
          :sort-field="activeSortField"
          :sort-direction="activeSortDirection"
          :group-mode="tableState.table?.groupMode || groupMode"
          @state="tableStateChanged"
          @select="tableSelect"
          @focus="(record) => $emit('focus', { kind: 'object', record })"
          @inspect="$emit('inspect', $event)"
          @operate="operate"
          @scroll="$emit('result-scroll', $event)"
          @column="tableColumn"
          @sort="sortBy"
          @group="
            tableStateChanged({
              ...tableState,
              table: { ...tableState.table, groupMode: $event }
            })
          "
          @width="(name, width) => changeColumns('width', name, width)"
          @move="(name, target) => changeColumns('move', name, target)"
          @hide="changeColumns('hide', $event)"
          @view="selectTableView"
          @save-view="saveTableView"
          @toggle-group="closedGroups[$event] = !closedGroups[$event]"
          @edit="openCellEditor"
          @header-action="tableHeaderAction"
          @create-child="createParentChild"
        >
          <template #detail="{ record }">
            <NestedTable
              :ticket="ticket"
              :project="project"
              :state="expandedTables[record.__search_key__]"
              @close="expandedTables[record.__search_key__].open = false"
              @edit="openNestedEditor"
              @inspect="$emit('inspect', $event)"
              @action="tableAction"
              @cell-event="nestedCellEvent"
              @column="$emit('column', $event)"
            />
          </template>
          <template #cell="{ record, column: element, height }">
            <TableCell
              :element="element"
              :record="record"
              :height="height"
              :accent="accent"
              :data-type="definition.columns?.[element.field]?.data_type"
              :selected="tableSelection.includes(record.__search_key__)"
              @select="tableSelect([record], $event)"
              :cell="
                displayCells[record.__search_key__]?.[element.name] ||
                (cellError && element.cell?.server
                  ? { error: cellError }
                  : undefined)
              "
              :loading="cellsBusy"
              :editable="
                !readOnly && !serviceBusy && !taskBusy && !taskUncertain
              "
              :expanded="!!expandedDetails[record.__search_key__]"
              :nested-state="expandedTables[record.__search_key__]"
              :selected-task-preview="
                tableSelection.includes(record.__search_key__) &&
                tableSelection.includes(hoveredTaskCell?.key)
              "
              @task-hover="
                (active) => {
                  if (active)
                    hoveredTaskCell = {
                      key: record.__search_key__,
                      column: element.name
                    };
                  else if (
                    hoveredTaskCell?.key === record.__search_key__ &&
                    hoveredTaskCell.column === element.name
                  )
                    hoveredTaskCell = null;
                }
              "
              @expand="
                expandedDetails[record.__search_key__] =
                  !expandedDetails[record.__search_key__]
              "
              @inspect="$emit('inspect', record)"
              @action="
                (kind, cell, anchor) => tableAction(record, kind, cell, anchor)
              "
              @preview="(cell) => $refs.preview.open(record, cell)"
              @notes="
                (cell, process) => $refs.notes.open(record, cell, process)
              "
              @tasks="(cell, task) => $refs.notes.openTask(record, cell, task)"
              @task-edit="
                (cell, task, field, bounds) =>
                  openTaskEditor(record, cell, task, field, bounds)
              "
            />
          </template>
        </TableView>
        <div
          v-if="!records.length && !error && ownQuery && !started"
          class="table-message"
        >
          {{ t('Run a search to load records.') }}
        </div>
        <div v-else-if="!records.length && !error" class="table-message">
          <strong>{{ t('No records yet') }}</strong
          ><span>{{ t('Choose another type or change the filter.') }}</span>
        </div>
      </template>
      <footer
        v-if="ownQuery && definition.panel?.show_search_limit !== false"
        class="pagination panel-pagination"
        :aria-label="t('View pages')"
      >
        <span>{{ rowRange }}</span>
        <div>
          <AppButton
            label="← Previous"
            icon="MDI_CHEVRON_LEFT"
            :icon-only="mobile"
            :disabled="busy || page === 0"
            @click="changePage(-1)"
          /><AppButton
            label="Next →"
            icon="MDI_CHEVRON_RIGHT"
            :icon-only="mobile"
            :disabled="busy || !hasNext"
            @click="changePage(1)"
          />
        </div>
      </footer>
    </template>
    <FilePreview
      ref="preview"
      :ticket="ticket"
      :project="project"
      :search-type="definition?.search_type"
    />
    <NotesPanel
      ref="notes"
      :ticket="ticket"
      :project="project"
      :search-type="definition?.search_type"
      @saved="loadCells"
    />
    <section
      v-for="record in records.filter(
        (record) => expandedDetails[record.__search_key__]
      )"
      :key="record.__search_key__"
      class="table-journal-detail"
    >
      <header>
        {{ record.name || record.title || record.code
        }}<AppButton
          label="Close"
          icon="close"
          icon-only
          @click="expandedDetails[record.__search_key__] = false"
        />
      </header>
      <JournalDetails
        :ticket="ticket"
        :project="project"
        :search-key="record.__search_key__"
      />
    </section>
    <SnapshotCheckout
      v-if="checkoutVisited"
      ref="tableCheckout"
      :ticket="ticket"
      :project="checkoutProject"
    />
    <ObjectOperations
      v-if="targetRecord"
      ref="tableOperations"
      :ticket="ticket"
      :project="targetProject"
      :search-type="targetRecord.__search_key__.split('?')[0]"
      :operations="targetOperations"
      :selection="
        records.filter((record) =>
          tableSelection.includes(record.__search_key__)
        )
      "
      @inspect="$emit('inspect', $event)"
      @edit="openTableRecordForm"
      @edit-selected="openTableRecordForm"
      @create="openTableRecordForm(null)"
      @duplicate="openTableRecordForm(null, $event.__search_key__)"
      @related="openTableRelations"
      @retire="$refs.tableDelete.open($event, 'retire')"
      @reactivate="$refs.tableDelete.open($event, 'reactivate')"
      @delete="$refs.tableDelete.open($event, 'delete')"
      @duplicated="tableSaved"
      @files-attached="tableSaved"
    />
    <ObjectAction
      v-if="targetRecord"
      ref="tableDelete"
      :ticket="ticket"
      :project="targetProject"
      :search-type="targetRecord.__search_key__.split('?')[0]"
      :view="
        targetRecord.__search_key__.split('?')[0] ===
        definition.search_type.split('?')[0]
          ? table.view || 'table'
          : 'table'
      "
      @saved="tableSaved"
    />
    <p v-if="serviceMessage" class="notice" role="status">
      {{ serviceMessage }}
    </p>
    <RecordForm
      v-if="targetRecord"
      ref="tableForm"
      :ticket="ticket"
      :project="targetProject"
      :edit-view="targetEditView"
      :ignore-fields="targetIgnore"
      :insert-view="targetInsertView"
      :search-type="targetRecord.__search_key__.split('?')[0]"
      @saved="tableSaved"
    />
    <RecordForm
      v-if="nestedEditor"
      ref="nestedForm"
      :ticket="ticket"
      :project="nestedEditor.scope.projectCode || project"
      :search-type="nestedEditor.scope.searchType"
      :edit-view="nestedEditor.scope.editView || 'edit'"
      :insert-view="nestedEditor.scope.insertView || 'insert'"
      @saved="tableSaved"
    />
    <TableServiceDialogs ref="tableServiceDialogs" />
    <TableParentPicker
      ref="parentPicker"
      :ticket="ticket"
      :project="project"
      @saved="tableSaved"
    />
    <TableDocument
      ref="tableDocument"
      :model="serviceDocument"
      :ticket="ticket"
      :project="project"
      @table-action="tableAction"
      @edit="openNestedEditor"
      @inspect="$emit('inspect', $event)"
      @cell-event="nestedCellEvent"
      @column="$emit('column', $event)"
      @saved="tableSaved"
      @notice="serviceMessage = $event"
      @file="openDependencyFile"
      @closed="documentRequest++"
      @action="
        (action) =>
          tableAction(
            serviceDocument.record,
            action.name,
            {
              ...serviceDocument,
              href: action.href,
              displayOptions: { cbjs_action: action.javascript }
            },
            $refs.tableDocument
          )
      "
    />
    <RelatedObjects
      v-if="targetRecord && relatedVisited"
      ref="tableRelated"
      :ticket="ticket"
      :project="targetProject"
      :search-type="targetRecord.__search_key__.split('?')[0]"
      @saved="tableSaved"
    />
    <TaskTableEditor
      ref="taskEditor"
      :editor="taskEditor"
      :busy="taskBusy"
      @change="stageTask"
      @closed="taskEditor = null"
    />
    <TableInlineEditor
      ref="inlineEditor"
      :editor="cellEditor"
      :busy="editBusy"
      :error="editError"
      :uncertain="editUncertain"
      @save="saveCellEditor"
      @check="saveCellEditor($event, true)"
      @cancel="cancelCellEditor"
    />
  </div>
</template>
