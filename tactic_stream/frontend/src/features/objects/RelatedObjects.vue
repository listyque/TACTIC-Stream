<script>
import { nextTick } from 'vue';
import {
  objectRelations,
  interfaceDefinition,
  resultItems,
  searchConfiguration,
  rpc
} from '../../api.js';
import { t } from '../../i18n.js';
import ConfiguredView from '../interface/ConfiguredView.vue';
import RecordForm from './RecordForm.vue';
import ObjectOperations from './ObjectOperations.vue';
import ObjectAction from './ObjectAction.vue';
import ObjectReport from './ObjectReport.vue';
import ObjectLinkSurface from './ObjectLinkSurface.vue';
import * as LinkUI from '../../../../src/tactic_stream/shared_ui/features/objects/links.ui.mjs';
import AppButton from '../../controls/AppButton.vue';
import AppSelect from '../../controls/AppSelect.vue';
import AppMenu from '../../controls/AppMenu.vue';
import { mobile } from '../../mobile.js';

export default {
  // Resolve the ConfiguredView / RelatedObjects module cycle lazily.
  components: {
    ObjectLinkSurface,
    ObjectReport,
    get ConfiguredView() {
      return ConfiguredView;
    },
    RecordForm,
    ObjectOperations,
    ObjectAction,
    AppButton,
    AppSelect,
    AppMenu
  },
  props: { ticket: String, project: String, searchType: String },
  inject: { openWorkspaceObjectTab: { from: 'openObjectTab', default: null } },
  provide() {
    return {
      openObjectTab: async (key, project) => {
        if (this.saving || this.dirty)
          throw new Error('Save or discard changes before opening a new tab.');
        this.close();
        await this.openWorkspaceObjectTab(key, project);
      }
    };
  },
  emits: ['saved'],
  data() {
    return {
      parent: null,
      relations: [],
      selectedType: '',
      definition: null,
      detail: null,
      linking: false,
      scope: null,
      uncertain: false,
      availableRecords: [],
      availableSelected: [],
      linkedSelected: [],
      availableQuery: '',
      linkedQuery: '',
      direction: 'add',
      availableNext: false,
      availableOffset: 0,
      availableTotal: 0,
      availableRequest: 0,
      availableBusy: false,
      selectionAnchor: -1,
      linkBranch: null,
      readBranch: null,
      selectedKeys: [],
      originalKeys: [],
      linkedRecords: [],
      relationRows: null,
      saving: false,
      discard: false,
      busy: false,
      error: '',
      request: 0
    };
  },
  computed: {
    linkValid() {
      return (
        this.scope?.ticket === this.ticket &&
        this.scope?.project === this.project
      );
    },
    linkModel() {
      return {
        targetTitle: this.relation?.title || this.selectedType,
        parentTitle:
          this.parent?.name || this.parent?.title || this.parent?.code,
        subtitle: this.linkBranch?.path || this.selectedType,
        direction: this.direction,
        selectedCount:
          this.direction === 'add'
            ? this.availableSelected.length
            : this.linkedSelected.length,
        canTransfer:
          this.direction === 'add'
            ? this.availableSelected.length > 0
            : this.linkedSelected.length > 0,
        dirty: this.dirty,
        busy: this.busy || this.availableBusy || this.saving,
        saving: this.saving,
        error: this.error,
        uncertain: this.uncertain,
        valid: this.linkValid
      };
    },
    availableLinkRows() {
      return this.availableRecords
        .filter(
          (row) =>
            !this.selectedKeys.includes(row.__search_key__) &&
            row.__search_key__ !== this.parent?.__search_key__
        )
        .map(this.linkRow);
    },
    linkedLinkRows() {
      return this.linkedRecords
        .filter(
          (row) =>
            this.selectedKeys.includes(row.__search_key__) &&
            (!this.linkedQuery ||
              [row.name, row.code, row.description]
                .join(' ')
                .toLocaleLowerCase()
                .includes(this.linkedQuery.toLocaleLowerCase()))
        )
        .map(this.linkRow);
    },
    mobile() {
      return mobile.value;
    },
    relation() {
      return this.relations.find(
        (item) => item.search_type === this.selectedType
      );
    },
    dirty() {
      return (
        this.linking &&
        JSON.stringify([...this.selectedKeys].sort()) !==
          JSON.stringify([...this.originalKeys].sort())
      );
    }
  },
  watch: {
    ticket() {
      this.invalidate();
    },
    project() {
      this.invalidate();
    },
    searchType() {
      this.invalidate();
    }
  },
  beforeUnmount() {
    this.request++;
    this.availableRequest++;
  },
  methods: {
    t,
    linkRecord(item) {
      return {
        ...item.record,
        __preview_url__: item.preview?.image || ''
      };
    },
    linkRow(row) {
      return {
        key: row.__search_key__,
        title: row.name || row.title || row.code || String(row.id),
        subtitle: row.description || '',
        previewUrl: row.__preview_url__ || '',
        accent: this.relation?.accent || 'action'
      };
    },
    linkAction(event) {
      if (event.type === 'transfer')
        this.transferLinks(
          this.direction === 'add' ? 'linked' : 'available',
          this.direction === 'add'
            ? this.availableSelected
            : this.linkedSelected
        );
      else if (event.type === 'save') this.saveLinks();
      else if (event.type === 'close') this.close();
      else if (event.type === 'refresh') this.openLinksAgain();
    },
    async openLinksAgain() {
      if (this.dirty || this.uncertain) return;
      await this.loadAvailable(false);
    },
    queryLinks(scope, value, commit) {
      this[scope + 'Query'] = value;
      if (scope === 'available' && commit) this.loadAvailable(false);
    },
    selectLink(scope, key, modifiers) {
      const records =
        scope === 'available' ? this.availableLinkRows : this.linkedLinkRows;
      const index = records.findIndex((row) => row.key === key);
      this[scope + 'Selected'] = LinkUI.select(
        this[scope + 'Selected'],
        records,
        index,
        this.direction === (scope === 'available' ? 'add' : 'remove')
          ? this.selectionAnchor
          : -1,
        modifiers.control,
        modifiers.shift
      );
      this.direction = scope === 'available' ? 'add' : 'remove';
      this[scope === 'available' ? 'linkedSelected' : 'availableSelected'] = [];
      this.selectionAnchor = index;
    },
    transferLinks(destination, keys) {
      if (this.saving || this.uncertain || !this.linkValid) return;
      const records = [...this.availableRecords, ...this.linkedRecords];
      const allowed = new Set(records.map((row) => row.__search_key__));
      keys = keys.filter(
        (key) => allowed.has(key) && key !== this.parent.__search_key__
      );
      if (destination === 'linked') {
        this.selectedKeys = [...new Set([...this.selectedKeys, ...keys])];
        this.linkedRecords = [
          ...new Map(
            records
              .filter((row) => this.selectedKeys.includes(row.__search_key__))
              .map((row) => [row.__search_key__, row])
          ).values()
        ];
      } else
        this.selectedKeys = this.selectedKeys.filter(
          (key) => !keys.includes(key)
        );
      this.availableSelected = [];
      this.linkedSelected = [];
      this.selectionAnchor = -1;
    },
    async loadAvailable(append) {
      if (
        !this.linkValid ||
        this.saving ||
        this.uncertain ||
        (append && this.availableBusy)
      )
        return;
      const request = ++this.availableRequest,
        scope = this.scope,
        offset = append ? this.availableOffset : 0;
      this.availableBusy = true;
      this.error = '';
      if (!append) {
        this.availableRecords = [];
        this.availableNext = false;
        this.availableSelected = [];
      }
      try {
        const columns = this.definition?.columns || {},
          field = columns.name
            ? 'name'
            : columns.code
              ? 'code'
              : Object.keys(columns)[0];
        const result = await searchConfiguration(
          'query',
          scope.ticket,
          scope.project,
          this.selectedType,
          {
            filters: this.availableQuery
              ? [[field, 'EQI', this.availableQuery]]
              : [],
            limit: 51,
            offset,
            order_bys: field ? [field] : [],
            include_total: true
          }
        );
        if (request !== this.availableRequest || !this.linkValid) return;
        const page = result.records.slice(0, 50);
        const details = page.length
          ? await resultItems(
              scope.ticket,
              scope.project,
              this.selectedType,
              page.map((row) => row.__search_key__)
            )
          : { items: [] };
        if (request !== this.availableRequest || !this.linkValid) return;
        const rows = details.items.map(this.linkRecord);
        this.availableRecords = append
          ? [...this.availableRecords, ...rows.slice(0, 50)]
          : rows.slice(0, 50);
        this.availableOffset = offset + Math.min(50, rows.length);
        this.availableNext = result.records.length > 50;
        this.availableTotal = result.total;
      } catch (error) {
        if (request === this.availableRequest) this.error = error.message;
      } finally {
        if (request === this.availableRequest) this.availableBusy = false;
      }
    },
    async open(record, searchType = '', linkBranch = null, readBranch = null) {
      if (this.$refs.dialog.open) return;
      const id = ++this.request;
      this.scope = { ticket: this.ticket, project: this.project };
      this.uncertain = false;
      this.availableRecords = [];
      this.availableSelected = [];
      this.linkedSelected = [];
      this.availableQuery = this.linkedQuery = '';
      this.direction = 'add';
      this.availableNext = false;
      this.availableOffset = 0;
      this.availableRequest++;
      this.availableBusy = false;
      this.parent = record;
      this.linking = !!linkBranch;
      this.linkBranch = linkBranch;
      this.readBranch = readBranch;
      this.discard = false;
      this.selectedKeys = [];
      this.originalKeys = [];
      this.linkedRecords = [];
      this.relationRows = null;
      this.relations = [];
      this.selectedType = '';
      this.definition = this.detail = null;
      this.busy = true;
      this.error = '';
      this.$refs.dialog.show();
      try {
        const result = await objectRelations(
          this.ticket,
          this.project,
          this.searchType,
          record.__search_key__
        );
        if (id !== this.request) return;
        this.parent = {
          ...record,
          __search_key__: this.linking
            ? record.__search_key__
            : result.search_key
        };
        this.relations = readBranch
          ? [{ ...readBranch, available: false }]
          : result.relations;
        this.selectedType =
          searchType ||
          result.relations.find((item) => item.available)?.search_type ||
          result.relations[0]?.search_type ||
          '';
        if (this.linking) {
          if (linkBranch.tableDrop)
            this.linkedRecords = linkBranch.links.map((link) => link.record);
          let offset = 0,
            next = !linkBranch.tableDrop;
          while (next) {
            const page = await resultItems(
              this.ticket,
              this.project,
              this.searchType,
              [this.parent.__search_key__],
              {
                branch: {
                  kind: 'relation',
                  search_type: searchType,
                  path: linkBranch.path
                },
                offset,
                limit: 100
              }
            );
            if (id !== this.request) return;
            this.linkedRecords.push(...page.items.map(this.linkRecord));
            offset += page.items.length;
            next = page.has_next;
          }
          this.originalKeys = this.linkedRecords.map(
            (item) => item.__search_key__
          );
          this.selectedKeys = [...this.originalKeys];
        }
        await this.load();
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    async openDrop(record, cell) {
      if (this.$refs.dialog.open)
        throw new Error('Apply or discard unsaved changes first');
      await this.open(record, cell.acceptedType, {
        ...cell.relation,
        links: cell.links,
        tableDrop: {
          search_type: this.searchType,
          view: cell.tableView,
          column: cell.columnName,
          expected_revision: cell.expectedRevision,
          parent_key: record.__search_key__
        }
      });
    },
    async stageDropped(keys) {
      if (
        !this.linkValid ||
        this.saving ||
        this.busy ||
        this.uncertain ||
        !Array.isArray(keys) ||
        keys.length > 500
      )
        return;
      const id = this.request,
        scope = this.scope,
        type = this.selectedType;
      if (
        keys.some(
          (key) => typeof key !== 'string' || key.split('?')[0] !== type
        )
      )
        throw new Error('Dropped objects belong to another Search Type');
      this.availableBusy = true;
      try {
        const records = await rpc('get_by_search_key', [scope, keys]);
        if (id !== this.request || !this.linkValid) return;
        if (records.some((record) => !record))
          throw new Error('A linked object is no longer available');
        this.availableRecords = [
          ...new Map(
            [...this.availableRecords, ...records].map((record) => [
              record.__search_key__,
              record
            ])
          ).values()
        ];
        this.transferLinks('linked', keys);
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.availableBusy = false;
      }
    },
    async load() {
      const id = ++this.request;
      this.definition = null;
      this.error = '';
      this.busy = true;
      this.relationRows = null;
      try {
        if (
          this.readBranch ||
          this.linking ||
          this.relation?.available ||
          this.relation?.relationship === 'instance'
        ) {
          const definition = await interfaceDefinition(
            this.ticket,
            this.project,
            this.selectedType
          );
          if (id !== this.request) return;
          if (this.readBranch) {
            this.relationRows = [];
            let next = true;
            while (next) {
              const page = await resultItems(
                this.ticket,
                this.project,
                this.searchType,
                [this.parent.__search_key__],
                {
                  branch: {
                    kind: 'parent',
                    search_type: this.readBranch.search_type,
                    path: this.readBranch.path
                  },
                  offset: this.relationRows.length,
                  limit: 100
                }
              );
              if (id !== this.request) return;
              this.relationRows.push(...page.items.map((item) => item.record));
              next = page.has_next;
            }
          } else if (
            !this.linking &&
            this.relation.relationship === 'instance'
          ) {
            const owner = await resultItems(
              this.ticket,
              this.project,
              this.searchType,
              [this.parent.__search_key__]
            );
            if (id !== this.request) return;
            const related = owner.items[0].branches.find(
              (branch) => branch.search_type === this.selectedType
            );
            if (!related)
              throw new Error('Relationship is not in the project schema');
            this.relationRows = [];
            let next = true;
            while (next) {
              const page = await resultItems(
                this.ticket,
                this.project,
                this.searchType,
                [this.parent.__search_key__],
                {
                  branch: {
                    kind: 'relation',
                    search_type: this.selectedType,
                    path: related.path
                  },
                  offset: this.relationRows.length,
                  limit: 100
                }
              );
              if (id !== this.request) return;
              this.relationRows.push(...page.items.map((item) => item.record));
              next = page.has_next;
            }
          }
          this.definition = definition;
          if (this.linking) await this.loadAvailable(false);
        }
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    close(force = false) {
      if (this.saving) return;
      if (this.dirty && !force) {
        this.discard = true;
        return;
      }
      this.request++;
      this.availableRequest++;
      this.$refs.operations?.close();
      this.$refs.dialog?.close();
    },
    invalidate() {
      this.request++;
      this.availableRequest++;
      this.busy = this.availableBusy = false;
      if (this.$refs.dialog?.open)
        this.error =
          'Connection context changed. Close this form and reopen it before saving.';
    },
    select(records, selected) {
      const keys = records
        .map((item) => item.__search_key__)
        .filter((key) => key !== this.parent.__search_key__);
      this.selectedKeys = selected
        ? [...new Set([...this.selectedKeys, ...keys])]
        : this.selectedKeys.filter((key) => !keys.includes(key));
    },
    async saveLinks() {
      if (this.saving || !this.dirty || this.uncertain || !this.linkValid)
        return;
      this.saving = true;
      this.error = '';
      const id = ++this.request;
      try {
        await rpc('execute_cmd', [
          this.scope,
          this.linkBranch.tableDrop
            ? 'tactic.ui.table.DropElementEditCmd'
            : 'tactic.command.sobject_link_cmd.SObjectLinkCmd',
          this.linkBranch.tableDrop
            ? {
                ...this.linkBranch.tableDrop,
                action: 'save',
                target_keys: [...this.selectedKeys]
              }
            : {
                parent_key: this.parent.__search_key__,
                search_type: this.selectedType,
                path: this.linkBranch.path,
                insert_search_keys: this.selectedKeys.filter(
                  (key) => !this.originalKeys.includes(key)
                ),
                exclude_search_keys: this.originalKeys.filter(
                  (key) => !this.selectedKeys.includes(key)
                )
              }
        ]);
        if (id !== this.request) return;
        this.originalKeys = [...this.selectedKeys];
        this.saving = false;
        this.close();
        this.$emit('saved');
      } catch (error) {
        if (id === this.request) {
          this.uncertain = !error.status || error.status >= 500;
          this.error = this.uncertain
            ? 'The save result is unknown. Close this form and refresh the records before trying again.'
            : error.message;
        }
      } finally {
        if (id === this.request) this.saving = false;
      }
    },
    create(source = null) {
      this.$refs.form.open(null, source?.__search_key__ || null, {
        parent_key: this.parent.__search_key__
      });
    },
    refresh() {
      if (this.relationRows) this.load();
      else this.$refs.table?.load();
    },
    async inspect(record) {
      this.detail = record;
      await nextTick();
      this.$refs.details.show();
    },
    edit(record) {
      this.$refs.details?.close();
      this.$refs.form.open(record.__search_key__);
    },
    display(value) {
      return value == null
        ? 'вЂ”'
        : typeof value === 'object'
          ? JSON.stringify(value)
          : String(value);
    }
  }
};
</script>

<template>
  <dialog
    v-window="{ kind: linking ? 'link_sobjects' : undefined, type: 'window' }"
    ref="dialog"
    class="record-dialog related-objects"
    :class="{ 'link-objects': linking }"
    :aria-label="t(linking ? 'Link existing objects' : 'Related objects')"
    @cancel.prevent="close()"
  >
    <header>
      <div>
        <h2>{{ t(linking ? 'Link existing objects' : 'Related objects') }}</h2>
        <small>{{
          parent?.name || parent?.title || parent?.code || parent?.id
        }}</small>
      </div>
      <AppButton
        label="Close related objects"
        icon="close"
        icon-only
        :disabled="saving"
        @click="close()"
      />
    </header>
    <p v-if="error && !linking" class="error" role="alert">{{ t(error) }}</p>
    <div v-if="!linking" class="toolbar">
      <label
        ><span v-if="!mobile">{{ t('Related type') }}</span
        ><AppSelect
          v-model="selectedType"
          label="Related type"
          :translate-labels="false"
          :options="
            relations.map((item) => ({
              value: item.search_type,
              label: mobile
                ? item.title
                : item.title + ' В· ' + item.search_type
            }))
          "
          :disabled="busy || !relations.length || !!readBranch"
          @update:model-value="load"
      /></label>
      <AppButton
        v-if="relation?.can_create && definition?.operations?.create"
        label="Create related object"
        icon="add"
        highlighted
        :icon-only="mobile"
        @click="create()"
      />
    </div>
    <ObjectLinkSurface
      v-if="linking"
      :model="linkModel"
      :available="availableLinkRows"
      :linked="linkedLinkRows"
      :available-selected="availableSelected"
      :linked-selected="linkedSelected"
      :ticket="scope?.ticket"
      :project="scope?.project"
      :search-type="selectedType"
      :available-query="availableQuery"
      :linked-query="linkedQuery"
      :total="availableTotal"
      :has-more="availableNext"
      @event="linkAction"
      @query="queryLinks"
      @select="selectLink"
      @drop="transferLinks"
      @more="loadAvailable(true)"
    />
    <p v-if="busy && !linking" role="status">{{ t('Loading dataвЂ¦') }}</p>
    <p
      v-else-if="!linking && relation && !relation.available && !definition"
      class="notice"
    >
      {{ t('This relationship is not available in this browser yet.') }}
    </p>
    <div v-if="definition && !linking" class="table-container">
      <ConfiguredView
        ref="table"
        :definition="definition"
        :ticket="ticket"
        :project="project"
        :rows="relationRows"
        :parent-key="
          linking || relationRows ? undefined : parent.__search_key__
        "
        :configured="false"
        :read-only="false"
        :selection-enabled="linking && !saving"
        :selected-keys="selectedKeys"
        @select="select"
        @inspect="inspect"
        @operate="
          (record, event, node) => $refs.operations.open(record, event, node)
        "
      />
    </div>
    <div v-if="discard" class="notice" role="alert">
      <p>{{ t('Discard unsaved changes?') }}</p>
      <AppButton label="Continue editing" @click="discard = false" /><AppButton
        label="Discard"
        destructive
        @click="close(true)"
      />
    </div>
  </dialog>
  <ObjectOperations
    ref="operations"
    :ticket="ticket"
    :project="project"
    :search-type="selectedType"
    :show-related="false"
    :operations="{
      ...definition?.operations,
      create: !!relation?.can_create && !!definition?.operations?.create
    }"
    @inspect="inspect"
    @edit="edit"
    @create="create()"
    @duplicate="create"
    @duplicated="refresh"
    @retire="(record) => $refs.action.open(record, 'retire')"
    @reactivate="(record) => $refs.action.open(record, 'reactivate')"
    @delete="(record) => $refs.action.open(record, 'delete')"
  />
  <RecordForm
    ref="form"
    :ticket="ticket"
    :project="project"
    :search-type="selectedType"
    @saved="refresh"
  />
  <ObjectAction
    ref="action"
    :ticket="ticket"
    :project="project"
    :search-type="selectedType"
    view="table"
    @saved="refresh"
  />
  <dialog
    v-window="{ type: 'window' }"
    ref="details"
    class="record-dialog object-details"
    :aria-label="t('Object details')"
  >
    <template v-if="detail">
      <header>
        <div>
          <h2>{{ detail.name || detail.title || detail.code || detail.id }}</h2>
          <small>{{ detail.__search_key__ }}</small>
        </div>
        <div class="configuration-actions">
          <AppButton
            v-if="definition?.operations?.edit"
            label="Edit record"
            icon="edit"
            :icon-only="mobile"
            @click="edit(detail)"
          />
          <AppButton
            label="Close details"
            icon="close"
            :icon-only="mobile"
            @click="$refs.details.close()"
          />
        </div>
      </header>
      <ObjectReport :ticket="ticket" :project="project" :record="detail" />
    </template>
  </dialog>
</template>
<style>
.link-objects {
  width: min(1120px, calc(100vw - 32px));
  height: min(780px, calc(100dvh - 32px));
}
.link-objects[open] {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  gap: 0;
  padding: 0;
}
.app-window.link-objects > header {
  flex: none;
  margin: 0;
  padding: 2px 12px;
  min-height: 40px;
}

@media (max-width: 700px) {
  .related-objects[open] {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    gap: 6px;
  }
  .related-objects > header {
    margin: 0;
    flex-wrap: nowrap;
    gap: 8px;
    flex-shrink: 0;
  }
  .related-objects > header h2 {
    font-size: var(--text-body-large);
    margin: 0;
  }
  .related-objects > .toolbar {
    flex-shrink: 0;
    margin: 0;
    flex-wrap: nowrap;
  }
  .related-objects > p {
    margin: 4px 0;
    flex-shrink: 0;
  }
  .related-objects > .table-container {
    flex: 1;
    min-height: 0;
    max-height: none;
    border: 0;
    border-radius: 0;
    background: var(--surface);
  }
  .related-objects > footer {
    display: flex;
    flex-shrink: 0;
    justify-content: flex-end;
    gap: 6px;
    padding-bottom: env(safe-area-inset-bottom);
  }
}
</style>
