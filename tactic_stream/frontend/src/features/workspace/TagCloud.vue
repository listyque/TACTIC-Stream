<script>
// Handler TagCloudPopup.qml / view_state.py. This view owns only its catalog read.
import { nextTick } from 'vue';
import { searchConfiguration } from '../../api.js';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/popups.ui.mjs';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppTextField from '../../controls/AppTextField.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import QuickFilterChip from '../../controls/display/QuickFilterChip.vue';
import { filterGeometry } from '../../../../src/tactic_stream/shared_ui/controls/display/chips.mjs';
import { layoutTextWidth } from '../../controls/typography/textMetrics.js';
import {
  packTagRows,
  tagRowAt
} from '../../../../src/tactic_stream/shared_ui/controls/lists/chips.mjs';

export default {
  components: {
    FrameView,
    AppButton,
    AppIcon,
    AppMenu,
    AppTextField,
    BusyIndicator,
    QuickFilterChip
  },
  props: {
    ticket: String,
    project: String,
    searchType: String,
    tabId: String,
    selected: Array,
    disabled: Boolean,
    boundary: Object,
    overlay: Boolean,
    externalTrigger: Boolean
  },
  emits: ['apply'],
  data() {
    return {
      headerWidth: 400,
      records: [],
      column: '',
      loaded: false,
      search: '',
      busy: false,
      error: '',
      rows: [],
      top: 0,
      height: 0,
      request: 0,
      menuBoundary: null
    };
  },
  computed: {
    headerScene() {
      return UI.tagHeader(
        {
          busy: this.busy,
          selected: this.selected.length,
          disabled: this.disabled,
          search: this.search
        },
        this.headerWidth,
        appearance.language
      );
    },
    context() {
      return [this.ticket, this.project, this.searchType, this.tabId];
    },
    filtered() {
      const query = this.search.trim().toLowerCase();
      return this.records.filter((row) =>
        row.tag.toLowerCase().includes(query)
      );
    },
    cloudHeight() {
      const row = this.rows.at(-1);
      return row ? row.top + row.height : 0;
    },
    visibleRows() {
      const first = Math.max(0, tagRowAt(this.rows, this.top) - 1);
      return this.rows.slice(
        first,
        tagRowAt(this.rows, this.top + this.height) + 2
      );
    }
  },
  watch: {
    context() {
      this.request++;
      this.busy = this.loaded = false;
      this.records = [];
      this.column = '';
      this.error = '';
      this.$refs.menu.open = false;
    },
    filtered() {
      this.rows = [];
      this.$refs.viewport.scrollTop = 0;
      this.pack();
    }
  },
  mounted() {
    this.menuBoundary = this.boundary || this.$el.closest('.workspace-browser');
    this.measure = document.createElement('canvas').getContext('2d');
    this.resize = new ResizeObserver(() => this.pack());
    this.resize.observe(this.$refs.viewport);
    this.resize.observe(this.$refs.sizing);
  },
  beforeUnmount() {
    this.request++;
    this.resize.disconnect();
  },
  methods: {
    t,
    headerEvent(action) {
      if (action.type === 'search') this.search = action.value;
      else if (action.type === 'reload') this.load(true);
      else if (action.type === 'clearTags') this.select('');
      else if (action.type === 'firstTag') this.focusTag(0);
      else if (action.type === 'clearSearch') {
        this.search = '';
        this.$refs.search.focusControl('tagCloudSearchField');
      }
    },
    open(source, returnTarget) {
      if (!source) {
        this.$refs.menu.open = true;
        return;
      }
      this.menuBoundary = this.boundary || source.closest('.workspace-browser');
      const bounds = source.getBoundingClientRect();
      this.$refs.menu.openAt({
        clientX: bounds.left,
        clientY: bounds.bottom,
        target: returnTarget || source
      });
    },
    async toggled(event) {
      if (!event.target.open) return;
      this.search = '';
      this.$refs.viewport.scrollTop = 0;
      await nextTick();
      this.pack();
      this.$refs.search.focusControl('tagCloudSearchField');
      await this.load();
    },
    async load(force = false) {
      if (this.busy || (this.loaded && !force)) return;
      const request = ++this.request;
      this.busy = true;
      this.error = '';
      try {
        const catalog = await searchConfiguration(
          'tags',
          this.ticket,
          this.project,
          this.searchType
        );
        if (request !== this.request) return;
        this.records = catalog.records;
        this.column = catalog.column;
        this.loaded = true;
        this.error = !catalog.column
          ? 'This search type has no tag column.'
          : !this.records.length
            ? 'No tags found.'
            : '';
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) {
          this.busy = false;
          await nextTick();
          this.pack();
        }
      }
    },
    pack() {
      const viewport = this.$refs.viewport;
      if (!this.$refs.menu?.open || !viewport?.clientWidth || !this.measure)
        return;
      this.headerWidth = this.$refs.viewport.clientWidth - 24;
      const style = getComputedStyle(this.$refs.sizing);
      const padding = getComputedStyle(viewport);
      this.rows = packTagRows(
        this.filtered,
        viewport.clientWidth -
          parseFloat(padding.paddingLeft) -
          parseFloat(padding.paddingRight),
        (label, weight) => {
          this.measure.font =
            style.fontWeight +
            ' ' +
            filterGeometry(weight).fontSize +
            'px ' +
            style.fontFamily;
          return layoutTextWidth(label, this.measure.font);
        },
        t('ALL')
      );
      this.scrolled();
    },
    scrolled() {
      const viewport = this.$refs.viewport;
      this.top = Math.max(0, viewport.scrollTop - this.$refs.cloud.offsetTop);
      this.height = viewport.clientHeight;
    },
    select(tag) {
      const tags = tag
        ? this.selected.includes(tag)
          ? this.selected.filter((value) => value !== tag)
          : [...this.selected, tag]
        : [];
      this.$emit('apply', { tags, column: this.column });
    },
    async focusTag(index, event) {
      if (index < -1 || index >= this.filtered.length) {
        this.$refs.viewport.scrollTop = 0;
        return;
      }
      event?.preventDefault();
      const row = this.rows.find((row) =>
        row.cells.some((cell) => cell.index === index)
      );
      if (!row) return;
      const viewport = this.$refs.viewport,
        top = this.$refs.cloud.offsetTop + row.top;
      if (top < viewport.scrollTop) viewport.scrollTop = top;
      else if (top + row.height > viewport.scrollTop + viewport.clientHeight)
        viewport.scrollTop = top + row.height - viewport.clientHeight;
      this.scrolled();
      await nextTick();
      this.$refs.cloud
        .querySelector('[data-tag-index="' + index + '"]')
        ?.focus();
    }
  }
};
</script>

<template>
  <AppMenu
    ref="menu"
    class="tag-cloud"
    label="Tags"
    icon="MDI_TAG_MULTIPLE"
    :overlay="overlay"
    :external-trigger="externalTrigger"
    :close-on-select="false"
    :boundary="boundary || menuBoundary"
    @toggle="toggled"
  >
    <template #trigger
      ><AppIcon name="MDI_TAG_MULTIPLE" /><small
        v-if="selected.length"
        class="action-count"
        >{{ selected.length }}</small
      ></template
    >
    <div
      ref="viewport"
      class="tag-cloud-viewport"
      :aria-busy="busy"
      @scroll.passive="scrolled"
    >
      <FrameView
        ref="search"
        :scene="headerScene"
        :style="{ height: '90px', flex: 'none' }"
        @event="headerEvent"
      />
      <p
        v-if="!busy && (error || !filtered.length)"
        :role="error ? 'status' : undefined"
      >
        {{ t(error || 'No matching tags') }}
      </p>
      <div
        ref="cloud"
        class="tag-cloud-body"
        :style="{ height: cloudHeight + 'px' }"
      >
        <div
          v-for="row in visibleRows"
          :key="row.top"
          class="tag-cloud-row"
          :style="{ top: row.top + 'px', height: row.height + 'px' }"
        >
          <QuickFilterChip
            v-for="cell in row.cells"
            :key="cell.index"
            :data-tag-index="cell.index"
            :checked="
              cell.index < 0
                ? !selected.length
                : selected.includes(filtered[cell.index].tag)
            "
            :disabled="disabled"
            :emphasis="filtered[cell.index]?.weight || 0"
            :text="cell.index < 0 ? t('ALL') : filtered[cell.index].tag"
            :title="cell.index < 0 ? t('ALL') : filtered[cell.index].tag"
            :style="{ width: cell.width + 'px' }"
            @click="select(cell.index < 0 ? '' : filtered[cell.index].tag)"
            @keydown.tab="
              focusTag(cell.index + ($event.shiftKey ? -1 : 1), $event)
            "
          />
        </div>
      </div>
    </div>
    <span ref="sizing" class="tag-cloud-sizing quick-filter-chip">{{
      t('ALL')
    }}</span>
  </AppMenu>
</template>
