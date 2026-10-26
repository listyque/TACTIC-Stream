<script>
import { markRaw, nextTick } from 'vue';
import { resultItems, navigationLink } from '../../api.js';
import { t } from '../../i18n.js';
import { copyText, copyImage } from '../../controls/clipboard.js';
import { browserLink } from '../workspace/links.js';
import { notify } from '../activity/notifications.js';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import FilePreview from './FilePreview.vue';
import { fileBlob } from './previewFiles.js';
import { duplicateProfile } from './duplicateProfiles.js';
import { desktopReason } from '../../../../src/tactic_stream/shared_ui/features/objects/watch.ui.mjs';

export default {
  components: { AppButton, AppMenu, FilePreview },
  inject: {
    openObjectTab: { default: null },
    openExternalAgent: { default: null },
    canUseAgent: { default: () => () => false },
    currentLogin: { default: () => () => '' }
  },
  emits: [
    'inspect',
    'edit',
    'edit-selected',
    'create',
    'duplicate',
    'duplicated',
    'retire',
    'reactivate',
    'delete',
    'related',
    'create-related',
    'link-related',
    'unlink',
    'preview-opened',
    'preview-closed',
    'files-attached'
  ],
  props: {
    ticket: String,
    project: String,
    searchType: String,
    operations: Object,
    showRelated: { type: Boolean, default: true },
    selection: { type: Array, default: () => [] }
  },
  data() {
    return {
      record: null,
      node: null,
      snapshots: [],
      request: 0,
      busy: false,
      advanced: false,
      checkinComponent: null,
      ingestComponent: null,
      duplicateComponent: null,
      hasDuplicateProfile: false
    };
  },
  computed: {
    canAgent() {
      return !!this.openExternalAgent && this.canUseAgent();
    },
    kind() {
      return (
        this.node?.branch?.kind ||
        (this.record?.__search_key__?.startsWith('sthpw/snapshot?')
          ? 'snapshot'
          : this.record?.__search_key__?.startsWith('sthpw/file?')
            ? 'file'
            : 'object')
      );
    },
    process() {
      return this.node?.branch?.process || this.record?.process || '';
    },
    hasSnapshot() {
      return this.kind === 'snapshot' || this.snapshots.length > 0;
    },
    selected() {
      return this.selection.some(
        (row) => row.__search_key__ === this.record?.__search_key__
      ) && this.selection.length > 1
        ? this.selection
        : [];
    },
    skey() {
      return this.record?.__search_key__
        ? 'skey://' + this.record.__search_key__
        : '';
    },
    canCheckin() {
      return (
        !!this.record &&
        !!this.operations?.checkin &&
        this.kind !== 'file' &&
        this.kind !== 'relation'
      );
    }
  },
  watch: {
    ticket() {
      this.close();
    },
    project() {
      this.close();
    },
    searchType() {
      this.close();
    }
  },
  beforeUnmount() {
    this.close();
  },
  methods: {
    t,
    watchFolderReason: () => desktopReason,
    async quick(record, node, command, options = {}) {
      const id = ++this.request;
      this.record = record;
      this.node = node;
      this.snapshots = [];
      if (command === 'save' || command === 'append') {
        if (!this.canCheckin)
          throw new Error(
            t('This operation or object type is not available yet.')
          );
        return this.checkin(
          command === 'append' ? { ...options, append: true } : options
        );
      }
      if (command !== 'open') return;
      if (this.kind === 'object') {
        const result = await resultItems(
          this.ticket,
          this.project,
          record.__search_key__.split('?')[0],
          [record.__search_key__],
          { branch: { kind: 'versions' } }
        );
        if (id !== this.request) return;
        this.snapshots = result.items.filter(
          (item) => item.record.context !== 'icon'
        );
      }
      return this.openSnapshot();
    },
    async open(record, event, node = null) {
      const id = ++this.request;
      this.$refs.menu.close();
      this.record = record;
      this.node = node;
      this.snapshots = [];
      this.busy = false;
      this.advanced = false;
      this.hasDuplicateProfile = !!duplicateProfile(
        this.currentLogin(),
        this.project,
        record.__search_key__.split('?')[0]
      );
      await nextTick();
      if (id !== this.request) return;
      this.$refs.menu.openAt(event);
      if (['file', 'relation'].includes(this.kind)) return;
      this.busy = true;
      try {
        const result = await resultItems(
          this.ticket,
          this.project,
          record.__search_key__.split('?')[0],
          [record.__search_key__],
          {
            branch:
              this.kind === 'process'
                ? { kind: 'process', process: this.process }
                : { kind: 'versions' }
          }
        );
        if (id === this.request)
          this.snapshots = result.items.filter(
            (item) => item.record.context !== 'icon'
          );
      } catch (error) {
        if (id === this.request) notify('error', error.message);
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    close() {
      this.request++;
      this.busy = false;
      if (this.node) this.node.menuVisible = false;
      this.$refs.menu?.close();
    },
    run(operation) {
      const record = this.record;
      this.close();
      this.$emit(operation, record);
    },
    agent() {
      const records = this.selected.length ? this.selected : [this.record];
      this.close();
      this.openExternalAgent(records, this.project);
    },
    async copy(web = false) {
      const value = web
        ? new URL(browserLink(this.skey, this.project), location.origin).href
        : this.skey;
      try {
        await copyText(value);
        this.close();
        notify('info', web ? 'Web link copied' : 'Search key copied');
      } catch (error) {
        notify('error', error.message);
      }
    },
    async newTab() {
      const key = this.skey,
        project = this.project;
      this.close();
      try {
        await this.openObjectTab(key, project);
      } catch (error) {
        notify('error', error.message);
      }
    },
    async checkin(options = {}) {
      const record =
        options.revision && this.kind !== 'snapshot'
          ? this.snapshots[0]?.record || this.record
          : this.record;
      const process = this.process,
        context = this.node?.branch?.process || record?.context;
      this.close();
      const request = this.request;
      try {
        if (!this.checkinComponent)
          this.checkinComponent = markRaw(
            (await import('../checkin/ObjectCheckin.vue')).default
          );
        await nextTick();
        if (request === this.request)
          await this.$refs.checkin.open(record, {
            process,
            context,
            ...options
          });
      } catch (error) {
        if (request === this.request) notify('error', error.message);
      }
    },
    async ingest() {
      const parent = this.record,
        branch = this.node.branch;
      this.close();
      const request = this.request;
      try {
        if (!this.ingestComponent)
          this.ingestComponent = markRaw(
            (await import('../checkin/IngestFiles.vue')).default
          );
        await nextTick();
        if (request === this.request)
          await this.$refs.ingest.open(parent, branch);
      } catch (error) {
        if (request === this.request) notify('error', error.message);
      }
    },
    async duplicate(quick = false) {
      const record = this.record;
      this.close();
      const request = this.request;
      try {
        if (!this.duplicateComponent)
          this.duplicateComponent = markRaw(
            (await import('./DuplicateSObject.vue')).default
          );
        await nextTick();
        if (request === this.request)
          await this.$refs.duplicate.open(record, quick);
      } catch (error) {
        if (request === this.request) notify('error', error.message);
      }
    },
    async openSnapshot() {
      const record = this.record,
        snapshot =
          this.kind === 'snapshot' || this.kind === 'file'
            ? record
            : this.snapshots[0]?.record;
      this.close();
      const request = this.request;
      if (!snapshot) return;
      try {
        const target = await navigationLink(
          this.ticket,
          this.project,
          'skey://' + snapshot.__search_key__
        );
        if (request === this.request && target.preview)
          this.$refs.preview.open(record, {
            ...target.preview,
            loadFile: (file) => this.fileBlob(file)
          });
      } catch (error) {
        if (request === this.request) notify('error', error.message);
      }
    },
    fileBlob,
    async fileAction(action) {
      const key = this.record.__search_key__,
        ticket = this.ticket,
        project = this.project;
      this.close();
      const request = this.request;
      try {
        const target = await navigationLink(ticket, project, 'skey://' + key);
        if (request !== this.request) return;
        const file = target.preview?.files?.find(
          (file) => file.code === target.preview.fileCode
        );
        if (!file) throw new Error(t('Attachment file was not found'));
        if (action === 'copy_path') {
          await copyText(file.path);
          notify('info', 'Path copied');
        } else if (action === 'copy_web_path') {
          if (!file.href)
            throw new Error(t('No web path is configured for this file.'));
          await copyText(new URL(file.href, location.href).href);
          notify('info', 'Web link copied');
        } else {
          const blob = await this.fileBlob(file);
          if (request !== this.request) return;
          await copyImage(blob);
          notify('info', 'Image copied');
        }
      } catch (error) {
        if (request === this.request) notify('error', error.message);
      }
    }
  }
};
</script>

<template>
  <AppMenu
    ref="menu"
    class="object-operations"
    label="Object actions"
    modal
    overlay
    :width="244"
    @toggle="node && (node.menuVisible = $event.target.open)"
  >
    <template v-if="selected.length">
      <AppButton label="Object details" icon="info" @click="run('inspect')" />
      <AppButton
        v-if="operations?.edit"
        icon="MDI_TABLE_EDIT"
        @click="
          close();
          $emit('edit-selected', selected);
        "
        >{{
          t('Edit {count} Selected in DB Editor', { count: selected.length })
        }}</AppButton
      >
      <AppButton
        v-if="operations?.delete"
        destructive
        icon="delete"
        @click="
          close();
          $emit('delete', selected);
        "
        >{{
          t('Delete All Selected ({count})', { count: selected.length })
        }}</AppButton
      >
    </template>
    <template v-else-if="kind === 'file'">
      <AppButton label="Open File" icon="folder" @click="openSnapshot" />
      <AppButton
        label="Show Folder"
        icon="folder"
        disabled
        :title="
          t(
            'Opening local folders requires a desktop connection. Use Open snapshot to view and download files in the browser.'
          )
        "
      />
      <hr />
      <AppButton
        label="Copy File Path"
        icon="copy"
        @click="fileAction('copy_path')"
      />
      <AppButton
        label="Copy Web Link"
        icon="link"
        @click="fileAction('copy_web_path')"
      />
      <AppButton
        label="Copy To Clipboard"
        icon="copy"
        @click="fileAction('copy_image')"
      />
    </template>
    <template v-else>
      <template v-if="kind === 'relation'">
        <AppButton
          v-if="operations?.create && operations?.checkin"
          label="Add files"
          icon="upload"
          @click="ingest"
        />
        <AppButton
          v-if="operations?.create"
          label="Add new Related sObject"
          icon="add"
          @click="run('create-related')"
        />
        <AppButton
          v-if="node.branch.relationship === 'instance'"
          label="Link sObjects Interface"
          icon="link"
          @click="run('link-related')"
        />
      </template>
      <template v-else>
        <AppButton
          v-if="hasSnapshot || kind === 'file'"
          label="Open snapshot"
          icon="folder"
          :disabled="busy"
          @click="openSnapshot"
        />
        <AppButton
          v-if="canCheckin"
          label="Save snapshot"
          icon="save"
          @click="checkin()"
        />
        <hr v-if="canCheckin" />
        <template v-if="kind === 'object' && advanced && operations?.create">
          <AppButton label="Duplicate…" icon="copy" @click="duplicate()" />
          <AppButton
            v-if="hasDuplicateProfile"
            label="Quick Duplicate"
            icon="copy"
            @click="duplicate(true)"
          />
          <AppButton
            label="Duplicate fields only"
            icon="copy"
            @click="run('duplicate')"
          />
        </template>
        <AppButton
          v-if="kind === 'object' && advanced && canCheckin"
          label="Change Preview"
          icon="image"
          @click="checkin({ preview: true })"
        />
        <AppButton
          v-if="canCheckin"
          label="Save from Clipboard"
          icon="MDI_CONTENT_PASTE"
          @click="checkin({ clipboard: true })"
        />
        <AppButton
          v-if="hasSnapshot && canCheckin && (kind !== 'object' || advanced)"
          label="Add revision (override current file)"
          icon="history"
          :disabled="busy"
          @click="checkin({ revision: true })"
        />
        <hr />
        <AppButton
          label="Show Folder"
          icon="folder"
          disabled
          :title="
            t(
              'Opening local folders requires a desktop connection. Use Open snapshot to view and download files in the browser.'
            )
          "
        />
        <AppButton
          v-if="kind !== 'object' || advanced"
          label="Show Folder Versions"
          icon="folder"
          disabled
          :title="
            t(
              'Opening local folders requires a desktop connection. Use Open snapshot to view and download files in the browser.'
            )
          "
        />
        <AppButton
          v-if="kind === 'object' && advanced"
          label="Create Watch Folder"
          icon="MDI_EYE"
          disabled
          :title="t(watchFolderReason())"
        />
        <hr />
        <template v-if="kind !== 'object' || advanced">
          <AppButton
            label="Copy Search Key"
            icon="copy"
            :disabled="!record"
            @click="copy()"
          />
          <AppButton
            label="Copy Web Link"
            icon="link"
            :disabled="!record"
            @click="copy(true)"
          />
          <AppButton
            v-if="kind === 'object' && openObjectTab"
            label="Open On New Tab"
            icon="MDI_TAB"
            @click="newTab"
          />
          <AppButton
            label="Object details"
            icon="info"
            :disabled="!record"
            @click="run('inspect')"
          />
          <AppButton
            v-if="showRelated && kind === 'object'"
            label="Related objects"
            icon="link"
            @click="run('related')"
          />
        </template>
        <AppButton
          v-if="kind !== 'process' && operations?.edit"
          label="Edit record"
          icon="edit"
          :disabled="!record"
          @click="run('edit')"
        />
        <AppButton
          v-if="kind === 'object' && advanced && operations?.create"
          label="Create record"
          icon="add"
          @click="run('create')"
        />
        <AppButton
          v-if="
            node?.relationship === 'instance' ||
            node?.branch?.relationship === 'instance'
          "
          label="Unlink"
          icon="MDI_LINK_OFF"
          @click="run('unlink')"
        />
        <AppButton
          v-if="kind !== 'process' && record && operations?.retire"
          :label="
            record[operations.retire_column] === 'retired'
              ? 'Reactivate record'
              : 'Retire record'
          "
          icon="archive"
          @click="
            run(
              record[operations.retire_column] === 'retired'
                ? 'reactivate'
                : 'retire'
            )
          "
        />
        <AppButton
          v-if="kind !== 'process' && record && operations?.delete"
          label="Delete record"
          icon="delete"
          destructive
          @click="run('delete')"
        />
        <AppButton
          v-if="
            kind === 'snapshot' &&
            Number(record?.version) < 0 &&
            operations?.delete
          "
          label="Delete Whole Tree"
          icon="MDI_DELETE_FOREVER"
          destructive
          @click="run('delete')"
        />
      </template>
    </template>
    <template v-if="canAgent && ['object', 'snapshot'].includes(kind)">
      <hr />
      <AppButton label="External agent" icon="comment" @click="agent" />
    </template>
    <template v-if="kind === 'object' && !selected.length">
      <hr />
      <AppButton
        :label="advanced ? 'Basic menu' : 'Advanced menu'"
        icon="MDI_DOTS_HORIZONTAL"
        @click.stop="advanced = !advanced"
      />
    </template>
  </AppMenu>
  <component
    v-if="checkinComponent"
    :is="checkinComponent"
    ref="checkin"
    :ticket="ticket"
    :project="project"
    @attached="$emit('files-attached')"
  />
  <component
    v-if="ingestComponent"
    :is="ingestComponent"
    ref="ingest"
    :ticket="ticket"
    :project="project"
  />
  <component
    v-if="duplicateComponent"
    :is="duplicateComponent"
    ref="duplicate"
    :ticket="ticket"
    :project="project"
    @completed="$emit('duplicated', $event)"
  />
  <FilePreview
    ref="preview"
    :ticket="ticket"
    :project="project"
    :search-type="searchType"
    @opened="$emit('preview-opened')"
    @closed="$emit('preview-closed')"
  />
</template>
