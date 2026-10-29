<script>
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import AppButton from '../../controls/AppButton.vue';
import FilePreviewContent from './FilePreviewContent.vue';
export default {
  components: { AppButton, FilePreviewContent },
  props: { ticket: String, project: String, searchType: String },
  emits: ['session-expired', 'opened', 'closed'],
  data() {
    return { record: null, cell: null, selectedFile: null, loading: false };
  },
  computed: {
    mobile() {
      return mobile.value;
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
  methods: {
    t,
    windowContext() {
      const { loadFile, ...cell } = this.cell || {};
      return {
        project: this.project,
        route: {
          key: this.record.__search_key__,
          fileCode: this.selectedFile?.code || ''
        },
        state: { record: this.record, cell, download: !!loadFile }
      };
    },
    open(record, cell) {
      this.record = record;
      this.cell = cell;
      this.$refs.dialog.show();
      this.$emit('opened');
    },
    close() {
      this.$refs.dialog?.close();
      this.record = this.cell = null;
    }
  }
};
</script>
<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'file_preview', type: 'window', page: windowContext }"
      ref="dialog"
      class="record-dialog file-preview"
      :aria-label="t('File preview')"
      :aria-busy="loading"
      @cancel.prevent="close"
      @close="
        record = cell = null;
        selectedFile = null;
        loading = false;
        $emit('closed');
      "
    >
      <template v-if="cell">
        <header>
          <div>
            <h2>
              {{
                (mobile && selectedFile?.filename) ||
                record?.name ||
                record?.title ||
                record?.code ||
                record?.id
              }}
            </h2>
            <small v-if="!mobile">{{ record?.__search_key__ }}</small>
          </div>
          <AppButton
            label="Close preview"
            icon="close"
            icon-only
            autofocus
            @click="close"
          />
        </header>
        <FilePreviewContent
          ref="content"
          :record="record"
          :cell="cell"
          @selected="selectedFile = $event"
          @busy="loading = $event"
          @session-expired="$emit('session-expired')"
        />
      </template>
    </dialog>
  </Teleport>
</template>
<style>
.file-preview video,
.file-preview iframe {
  width: 100%;
  max-height: 55dvh;
  min-height: 200px;
  border: 0;
}
.file-preview audio {
  width: 100%;
}
.file-preview-text {
  max-height: 55dvh;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.file-preview-files > li {
  min-width: 0;
}
.file-preview-files strong {
  overflow-wrap: anywhere;
}
@media (max-width: 700px) {
  .file-preview.record-dialog[open] {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    gap: 6px;
  }
  .file-preview.record-dialog > header {
    flex-shrink: 0;
    flex-wrap: nowrap;
    margin: 0;
    gap: 8px;
  }
  .file-preview > header > div {
    flex: 1;
    min-width: 0;
  }
  .file-preview > header h2 {
    margin: 0;
    font-size: var(--text-body-large);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .file-preview > .app-select,
  .file-preview > p,
  .file-preview > .file-preview-details {
    flex-shrink: 0;
  }
  .file-preview > p {
    margin: 0;
  }
  .file-preview-content {
    flex: 1;
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
  }
  .file-preview-content .image-picker-preview {
    height: 100%;
    min-height: 0;
  }
  .file-preview video,
  .file-preview iframe {
    height: 100%;
    min-height: 0;
    max-height: none;
  }
  .file-preview-text {
    max-height: none;
    margin: 0;
    min-height: 100%;
  }
  .file-preview-details {
    align-self: flex-end;
    margin-bottom: env(safe-area-inset-bottom);
  }
  .file-preview-details .file-preview-metadata {
    font-size: var(--text-label);
    margin-block: 8px;
    gap: 6px;
  }
  .file-preview-files li {
    gap: 6px;
    padding-block: 8px;
  }
  .file-preview-files li > div:first-child {
    flex-basis: 100%;
  }
}
</style>
