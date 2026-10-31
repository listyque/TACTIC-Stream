<script setup>
// Only adapt named house controls and their events; layout lives in the shared catalog.
import { computed, ref } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import AttachmentCard from '../../controls/AttachmentCard.vue';
import PreviewNavigationButton from '../../controls/actions/PreviewNavigationButton.vue';
import DisclosureButton from '../../controls/actions/DisclosureButton.vue';
import StatusChip from '../../controls/display/StatusChip.vue';
import ReactionChip from '../../controls/display/ReactionChip.vue';
import EditorPanel from '../../controls/layout/EditorPanel.vue';
import ConfigurationSection from '../../controls/layout/ConfigurationSection.vue';
import SectionLabel from '../../controls/layout/SectionLabel.vue';
import InfoValueStrip from '../../controls/layout/InfoValueStrip.vue';
import FormFieldFrame from '../../controls/forms/FormFieldFrame.vue';
import EditorListItem from '../../controls/lists/EditorListItem.vue';
import UserGroupSection from '../../controls/UserGroupSection.vue';
import ProfileInfoRow from '../../controls/ProfileInfoRow.vue';
import AppTextField from '../../controls/AppTextField.vue';
import QuickFilterChip from '../../controls/display/QuickFilterChip.vue';
import ContentLoadingOverlay from '../../controls/display/ContentLoadingOverlay.vue';
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue';
import AppSlider from '../../controls/AppSlider.vue';
import AppSpinBox from '../../controls/forms/AppSpinBox.vue';
import AppSearchField from '../../controls/AppSearchField.vue';
import AppTabButton from '../../controls/AppTabButton.vue';
import StatusSelect from '../../controls/StatusSelect.vue';
import SummaryChip from '../../controls/SummaryChip.vue';
import UserIdentity from '../../controls/UserIdentity.vue';
import UserPicker from '../../controls/UserPicker.vue';
import EmojiPicker from '../../controls/EmojiPicker.vue';
import ImagePicker from '../../controls/ImagePicker.vue';
import AccentPresetPicker from '../../controls/AccentPresetPicker.vue';
import AppProgress from '../../controls/AppProgress.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import EmptyState from '../../controls/display/EmptyState.vue';
import DropTargetOverlay from '../../controls/display/DropTargetOverlay.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppMenuItem from '../../controls/AppMenuItem.vue';
import DocumentPane from '../../controls/DocumentPane.vue';
import MiddleElide from '../../controls/MiddleElide.vue';
import SettingRow from '../../controls/SettingRow.vue';
import AppSwitch from '../../controls/AppSwitch.vue';
import ResponsiveFlow from '../../controls/ResponsiveFlow.vue';
import QuickFilterOptions from '../../features/workspace/QuickFilterOptions.vue';
import { packedOptions } from '../../../../src/tactic_stream/shared_ui/controls/catalog/variants.mjs';
import { options } from '../../../../src/tactic_stream/shared_ui/controls/catalog/variants.mjs';
import { users } from '../../../../src/tactic_stream/shared_ui/controls/catalog.ui.mjs';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';

const props = defineProps({
  example: Object,
  value: [String, Number, Boolean, Array],
  disabled: Boolean,
  readonly: Boolean
});
const emit = defineEmits(['event']);
const data = computed(() => props.example.properties);
const choices = computed(() => options(props.example));
const suggestions = computed(() =>
  data.value.suggestions
    ? [
        { title: 'Robot Arm', description: 'Example', code: 'arm' },
        { title: 'Robot Body', description: 'Example', code: 'body' }
      ]
    : []
);
const image = ref(null);
const optionsViewport = ref(null),
  optionTop = ref(0);
const packed = computed(() => packedOptions(props.value));
const presets = [
  {
    value: 'blue',
    label: 'Blue',
    dark: '#78a6c4',
    light: '#3d7599',
    darkBase: '#292d30',
    lightBase: '#d4dce1'
  },
  {
    value: 'green',
    label: 'Green',
    dark: '#77b398',
    light: '#3d8062',
    darkBase: '#26342e',
    lightBase: '#d9e9df'
  }
];
const known = [
  'attachment',
  'segments',
  'spin',
  'slider',
  'search',
  'status',
  'users',
  'identity',
  'emoji',
  'image',
  'presets',
  'chip',
  'tab',
  'menu',
  'progress',
  'busy',
  'empty',
  'drop',
  'markdown',
  'elide',
  'setting',
  'flow',
  'counter',
  'disclosure',
  'previewNavigation',
  'send',
  'packedChoices',
  'statusChip',
  'reaction',
  'filterChip',
  'loadingOverlay',
  'editorPanel',
  'configurationSection',
  'sectionLabel',
  'infoValues',
  'fieldFrame',
  'listItem',
  'userGroup',
  'profileInfo'
];
if (!known.includes(props.example.kind))
  throw Error('Missing catalog brick: ' + props.example.kind);
function change(value) {
  if (!props.disabled && !props.readonly)
    emit('event', { type: 'change', value });
}
function activate(type = 'activate') {
  if (!props.disabled) emit('event', { type });
}
</script>

<template>
  <div class="control-example" :data-example="example.id">
    <AttachmentCard
      v-if="example.kind === 'attachment'"
      title="Robot Arm"
      :extension="data.extension"
      :preview-url="data.source || ''"
      size-text="128 KB"
      :compact="!!data.compact"
      :web-preview="false"
      :disabled="disabled || readonly"
      :style="{ width: '100%', height: '100%' }"
      @activated="activate()"
    />
    <AppSegmentedButton
      v-else-if="example.kind === 'segments'"
      :model-value="value"
      :options="choices"
      label="Display"
      :icon-only="data.iconOnly"
      :outlined="data.outlined"
      :disabled="disabled"
      @update:model-value="change"
    />
    <AppSpinBox
      v-else-if="example.kind === 'spin'"
      :model-value="value"
      :min="data.min"
      :max="data.max"
      :step="data.step"
      :decimals="data.decimals"
      label="Size"
      :disabled="disabled"
      :readonly="readonly"
      @update:model-value="change"
    />
    <AppSlider
      v-else-if="example.kind === 'slider'"
      :model-value="value"
      :min="data.min"
      :max="data.max"
      :step="data.step"
      label="Size"
      :disabled="disabled || readonly"
      @update:model-value="change"
    />
    <AppSearchField
      v-else-if="example.kind === 'search'"
      :model-value="value"
      label="Search"
      :placeholder="t('Search')"
      :suggestions="suggestions"
      :disabled="disabled"
      :readonly="readonly"
      @update:model-value="change"
      @search="activate('search')"
      @dismiss="activate('dismiss')"
      @open="activate('open')"
      @accept="change($event.title)"
    />
    <div
      v-else-if="example.kind === 'packedChoices'"
      ref="optionsViewport"
      class="example-options-viewport"
      @scroll.passive="optionTop = $event.target.scrollTop"
    >
      <QuickFilterOptions
        v-if="optionsViewport"
        :options="packed"
        :viewport="optionsViewport"
        :top="optionTop"
        :height="280"
        active
        :disabled="disabled"
        @activate="change"
      />
    </div>
    <StatusSelect
      v-else-if="example.kind === 'status'"
      :value="value"
      :options="choices"
      :disabled="disabled"
      @change="change"
    />
    <UserPicker
      v-else-if="example.kind === 'users'"
      :model-value="value"
      :users="users"
      :disabled="disabled"
      @update:model-value="change"
    />
    <UserIdentity
      v-else-if="example.kind === 'identity'"
      login="admin"
      display-name="Administrator"
      initials="A"
      avatar-color="#557f75"
      :retired="data.retired"
      :emphasized="data.emphasized"
      :avatar-size="data.avatarSize || 40"
    />
    <UserGroupSection
      v-else-if="example.kind === 'userGroup'"
      :title="value"
      :compact="data.compact"
    />
    <ProfileInfoRow
      v-else-if="example.kind === 'profileInfo'"
      icon="person"
      label="Name"
      :value="value"
    />
    <EmojiPicker
      v-else-if="example.kind === 'emoji'"
      :disabled="disabled"
      @selected="change"
    />
    <ImagePicker
      v-else-if="example.kind === 'image'"
      :model-value="image"
      :disabled="disabled"
      fallback-text="RA"
      @update:model-value="
        image = $event;
        change($event?.name || '');
      "
    />
    <AccentPresetPicker
      v-else-if="example.kind === 'presets'"
      :model-value="value"
      :options="presets"
      :mode="appearance.mode"
      label="Colors"
      :disabled="disabled"
      @update:model-value="change"
    />
    <SummaryChip
      v-else-if="example.kind === 'chip'"
      :label="t('Status')"
      :count="value"
      :compact="data.compact"
      :clickable="data.clickable"
      :disabled="data.clickable ? disabled : undefined"
      @click="activate()"
    />
    <StatusChip
      v-else-if="example.kind === 'statusChip'"
      :text="value"
      icon="check"
      accent="#55a9ad"
      :dense="data.dense"
      :interactive="data.interactive"
      :disabled="disabled"
      @click="activate()"
    />
    <ReactionChip
      v-else-if="example.kind === 'reaction'"
      emoji="👍"
      :count="data.count"
      :checked="value"
      :disabled="disabled"
      @click="change(!value)"
    />
    <QuickFilterChip
      v-else-if="example.kind === 'filterChip'"
      style="width: 100%; height: 100%"
      text="Example"
      icon="filter"
      :checked="value"
      :subtle="data.subtle"
      :show-accent-marker="data.marker"
      :emphasis="data.emphasis"
      :disabled="disabled"
      @click="change(!value)"
    />
    <ContentLoadingOverlay
      v-else-if="example.kind === 'loadingOverlay'"
      message="Loading…"
      :cancellable="data.cancellable"
      :disabled="disabled"
      @cancel="activate('cancel')"
    />
    <EditorPanel
      v-else-if="example.kind === 'editorPanel'"
      title="Name"
      description="Description"
      icon="settings"
      ><div class="example-body">Example</div></EditorPanel
    >
    <ConfigurationSection
      v-else-if="example.kind === 'configurationSection'"
      title="Name"
      description="Description"
      fill-content-height
      ><div class="example-body">Example</div></ConfigurationSection
    >
    <SectionLabel v-else-if="example.kind === 'sectionLabel'" text="Display" />
    <InfoValueStrip
      v-else-if="example.kind === 'infoValues'"
      :items="data.items"
    />
    <FormFieldFrame
      v-else-if="example.kind === 'fieldFrame'"
      title="Name"
      field-name="name"
      description="Description"
      icon="edit"
      :required="data.required"
      :readonly="readonly || data.readOnly"
      :error="data.error ? 'Invalid value' : ''"
    >
      <AppTextField
        :model-value="value"
        label="Name"
        :disabled="disabled"
        :readonly="readonly || data.readOnly"
        :error-state="data.error"
        @update:model-value="change"
      />
    </FormFieldFrame>
    <EditorListItem
      v-else-if="example.kind === 'listItem'"
      :text="value"
      description="Description"
      icon="folder"
      :selected="data.selected"
      :wrap-title="data.wrapTitle"
      :badge-text="data.badge ? '4' : ''"
      :disabled="disabled"
      @click="activate()"
    />
    <AppTabButton
      v-else-if="example.kind === 'tab'"
      label="Display"
      :checked="value"
      :disabled="disabled"
      @click="change(!value)"
    />
    <AppMenu
      v-else-if="example.kind === 'menu'"
      label="Actions"
      :disabled="disabled"
      overlay
    >
      <AppMenuItem
        label="Refresh"
        icon="refresh"
        @click="activate('refresh')"
      />
      <AppMenuItem
        label="Enabled"
        :checked="data.checkable ? !!value : undefined"
        @click="change(!value)"
      />
      <AppMenuItem label="Delete" icon="delete" disabled />
    </AppMenu>
    <AppProgress
      v-else-if="example.kind === 'progress'"
      label="Progress"
      :value="value === null ? undefined : value"
    />
    <BusyIndicator
      v-else-if="example.kind === 'busy'"
      :running="value && !disabled"
    />
    <EmptyState
      v-else-if="example.kind === 'empty'"
      :error="data.error"
      :icon="data.error ? 'warning' : 'info'"
      :title="data.error ? 'Error' : 'No records yet'"
      message="Description"
      :action="
        data.error
          ? { label: 'Retry', icon: 'refresh', command: 'retry', disabled }
          : null
      "
      @action="activate"
    />
    <DropTargetOverlay
      v-else-if="example.kind === 'drop'"
      :accepted="data.accepted"
      :prompt="data.accepted ? 'Drop files here' : 'Unsupported file type'"
    />
    <DocumentPane
      v-else-if="example.kind === 'markdown'"
      document-key="example"
      :text="value"
      @link="activate('link')"
    />
    <MiddleElide v-else-if="example.kind === 'elide'" :text="value" />
    <SettingRow
      v-else-if="example.kind === 'setting'"
      control-id="exampleSetting"
      title="Enabled"
      description="Description"
    >
      <AppSwitch
        id="exampleSetting"
        :model-value="value"
        label="Enabled"
        :disabled="disabled"
        @update:model-value="change"
      />
    </SettingRow>
    <ResponsiveFlow
      v-else-if="example.kind === 'flow'"
      :minimum-cell-width="120"
    >
      <AppButton
        v-for="option in choices"
        :key="option.value"
        :label="option.label"
        :disabled="disabled"
        @click="change(option.value)"
      />
    </ResponsiveFlow>
    <AppButton
      v-else-if="example.kind === 'counter'"
      icon="comment"
      icon-only
      label="Notes"
      :badge-count="value"
      badge-color="var(--primary)"
      :style="{ color: value > 0 ? 'var(--primary)' : 'var(--muted)' }"
      :disabled="disabled"
      @click="activate()"
    />
    <DisclosureButton
      v-else-if="example.kind === 'disclosure'"
      :expanded="value"
      identity="sample"
      has-children
      :disabled="disabled"
      @click="change(!value)"
    />
    <PreviewNavigationButton
      v-else-if="example.kind === 'previewNavigation'"
      label="Next"
      :disabled="disabled"
      @click="activate()"
    />
    <AppButton
      v-else-if="example.kind === 'send'"
      :label="value ? 'Sending' : 'Send'"
      icon="send"
      compact
      highlighted
      :disabled="disabled || value"
      @click="change(true)"
    />
  </div>
</template>

<style>
.control-example {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
}
.control-example > .app-button,
.control-example > .app-tab-button.app-button:not(.icon-button),
.control-example > .workspace-menu {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
}
.control-example > .workspace-menu > summary {
  display: inline-flex;
  width: auto;
  height: 100%;
  aspect-ratio: 1;
  min-width: 0;
  min-height: 0;
}
.control-example
  > :is(
    .app-segmented-button,
    .app-spin-box,
    .app-slider,
    .app-search-field,
    .status-select,
    .user-identity,
    .empty-state,
    .app-tab-button
  ) {
  width: 100%;
  height: 100%;
}
.control-example > .app-menu,
.control-example > .summary-chip {
  max-width: 100%;
}
.control-example
  > :is(
    .summary-chip,
    .accent-preset-picker,
    .image-picker,
    .busy-indicator,
    .document-pane,
    .settings-row,
    .responsive-flow
  ) {
  width: 100%;
  height: 100%;
  margin: 0;
}
.control-example > .busy-indicator {
  width: 24px;
  height: 24px;
}
.control-example > .middle-elide {
  line-height: 36px;
}
.control-example .user-picker {
  height: 100%;
}
.control-example
  > :is(
    .status-chip,
    .reaction-chip,
    .editor-panel,
    .configuration-section,
    .section-label,
    .info-value-strip,
    .form-field-frame,
    .editor-list-item-surface,
    .user-group-section,
    .profile-info-row
  ) {
  width: 100%;
  height: 100%;
}
.example-body {
  display: grid;
  place-items: center;
  flex: 1;
  height: 100%;
  min-height: 0;
  background: var(--surface-high);
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
}
.control-example > .reaction-chip.app-button {
  width: 100%;
  height: 100%;
}
.control-example > .quick-filter-chip.app-button {
  width: 100%;
  height: 100%;
}
.example-options-viewport {
  width: 100%;
  height: 100%;
  overflow: auto;
  scrollbar-gutter: stable;
}
</style>
