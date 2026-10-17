<script>
import { objectDeletion, objectStatus, rpc } from '../../api.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import ObjectDeleteSurface from './ObjectDeleteSurface.vue';

export default {
  components: { AppButton, ObjectDeleteSurface },
  inject: { openHelp: { default: null } },
  props: { ticket: String, project: String, searchType: String, view: String },
  emits: ['saved'],
  data() {
    return {
      record: null,
      records: [],
      operation: '',
      context: null,
      groups: [],
      selected: [],
      ready: false,
      loading: false,
      saving: false,
      error: '',
      uncertain: false,
      request: 0
    };
  },
  computed: {
    title() {
      return (
        {
          retire: 'Retire record',
          reactivate: 'Reactivate record',
          delete: 'Delete record'
        }[this.operation] || 'Object actions'
      );
    },
    deleteModel() {
      return {
        targetCount: this.records.length,
        targets: this.records.map((record) => ({
          title:
            record.name || record.title || record.code || String(record.id),
          searchKey: record.__search_key__
        })),
        ready: this.ready,
        busy: this.loading,
        deleting: this.saving,
        error: this.error,
        uncertain: this.uncertain,
        groups: this.groups.map((group) => ({
          searchType: group.search_type,
          searchTypeTitle: group.title,
          iconName:
            {
              'sthpw/snapshot': 'snapshot',
              'sthpw/note': 'notes',
              'sthpw/task': 'tasks',
              'sthpw/status_log': 'history'
            }[group.search_type] || 'sobject',
          count: group.count,
          checked: this.selected.includes(group.search_type),
          defaultChecked: group.selected,
          expanded: !!group.expanded,
          items: group.items || []
        }))
      };
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
    },
    view() {
      this.invalidate();
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
  },
  beforeUnmount() {
    this.request++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    deleteEvent(event) {
      if (event.type === 'delete') this.apply();
      else if (event.type === 'cancel') this.close();
      else if (event.type === 'help') this.openHelp?.('deleting_objects');
      else if (event.type === 'retry') this.loadDeletion();
      else if (event.type === 'expand')
        this.groups[event.index].expanded = !this.groups[event.index].expanded;
      else if (event.type === 'check') {
        const type = this.groups[event.index].search_type;
        this.selected = event.value
          ? [...new Set([...this.selected, type])]
          : this.selected.filter((value) => value !== type);
      }
    },
    invalidate() {
      this.request++;
      this.uncertain = true;
      this.error =
        'Connection context changed. Close this form and reopen it before saving.';
    },
    beforeUnload(event) {
      if (this.saving || (this.uncertain && this.$refs.dialog.open)) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    close(event) {
      if (this.saving) {
        event?.preventDefault();
        return;
      }
      this.request++;
      this.$refs.dialog.close();
    },
    async open(record, operation) {
      if (this.$refs.dialog.open) return;
      ++this.request;
      this.records = Array.isArray(record) ? [...record] : [record];
      if (!this.records.length) return;
      this.record = this.records[0];
      this.operation = operation;
      this.groups = [];
      this.selected = [];
      this.error = '';
      this.uncertain = false;
      this.ready = false;
      this.context = {
        ticket: this.ticket,
        project: this.project,
        searchType: this.searchType,
        view: this.view
      };
      this.loading = operation === 'delete';
      this.$refs.dialog.showModal();
      if (!this.loading) return;
      await this.loadDeletion();
    },
    async loadDeletion() {
      if (this.saving || this.uncertain) return;
      const id = ++this.request;
      this.loading = true;
      this.ready = false;
      this.error = '';
      try {
        const context = this.context;
        const definition = await objectDeletion(
          'read',
          context.ticket,
          context.project,
          context.searchType,
          context.view,
          this.records.map((record) => record.__search_key__)
        );
        if (id !== this.request) return;
        this.groups = definition.groups;
        this.selected = definition.groups
          .filter((group) => group.selected)
          .map((group) => group.search_type);
        this.ready = true;
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.loading = false;
      }
    },
    async apply() {
      if (
        this.loading ||
        this.saving ||
        this.uncertain ||
        (this.operation === 'delete' && !this.ready)
      )
        return;
      const id = this.request,
        context = this.context;
      this.saving = true;
      this.error = '';
      try {
        const keys = this.records.map((record) => record.__search_key__);
        if (this.operation === 'delete')
          await objectDeletion(
            'apply',
            context.ticket,
            context.project,
            context.searchType,
            context.view,
            keys,
            this.selected
          );
        else if (keys.length > 1)
          await objectStatus(
            context.ticket,
            context.project,
            context.searchType,
            context.view,
            keys,
            this.operation
          );
        else
          await rpc(
            this.operation === 'retire'
              ? 'retire_sobject'
              : 'reactivate_sobject',
            [
              { ticket: context.ticket, project: context.project },
              this.record.__search_key__
            ]
          );
        if (id !== this.request) return;
        this.$refs.dialog.close();
        this.$emit('saved');
      } catch (error) {
        if (id !== this.request) return;
        this.error = error.message;
        this.uncertain = !error.status || error.status >= 500;
      } finally {
        this.saving = false;
      }
    }
  }
};
</script>

<template>
  <dialog
    v-window="{
      kind: operation === 'delete' ? 'delete_sobject' : '',
      type: 'dialog'
    }"
    ref="dialog"
    class="record-dialog object-action"
    :class="{ 'object-deletion': operation === 'delete' }"
    :aria-label="t(title || 'Object actions')"
    @cancel="close"
  >
    <header>
      <div>
        <h2>{{ t(title) }}</h2>
        <small>{{
          record?.name || record?.title || record?.code || record?.id
        }}</small>
      </div>
      <AppButton
        label="Close actions"
        icon="close"
        icon-only
        :disabled="saving"
        @click="close"
      />
    </header>
    <ObjectDeleteSurface
      v-if="operation === 'delete'"
      :model="deleteModel"
      @event="deleteEvent"
    />
    <p v-else>
      {{
        t(
          operation === 'retire'
            ? 'Retiring keeps the data and hides the object from normal searches.'
            : 'Reactivating returns the object to normal searches.'
        )
      }}
    </p>
    <p v-if="error && operation !== 'delete'" class="error" role="alert">
      {{ t(error) }}
    </p>
    <p v-if="uncertain" class="notice">
      {{
        t(
          'This operation cannot be retried here. Close this dialog and refresh the data to check the result.'
        )
      }}
    </p>
    <footer v-if="operation !== 'delete'" class="configuration-actions">
      <button type="button" :disabled="saving" @click="close">
        {{ t('Cancel') }}
      </button>
      <button
        type="button"
        :class="operation === 'delete' ? 'danger' : 'primary'"
        :disabled="loading || saving || uncertain"
        @click="apply"
      >
        {{ t(saving ? 'Applying…' : title) }}
      </button>
    </footer>
  </dialog>
</template>

<style>
.object-deletion.record-dialog {
  width: min(900px, calc(100vw - 32px));
  height: min(680px, calc(100dvh - 32px));
  padding: 0;
}
.object-deletion[open] {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.object-deletion > header {
  flex: none;
  padding: 12px 16px;
  margin: 0;
}
.object-deletion > .notice {
  flex: none;
  margin: 8px 16px;
}
</style>
