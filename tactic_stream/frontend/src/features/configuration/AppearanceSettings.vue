<script setup>
import {
  appearance,
  effectiveColorMode,
  languages,
  themes,
  colorModes,
  iconSets,
  accentPresets
} from '../../appearance.js';
import { t } from '../../i18n.js';
import AppIcon from '../../controls/AppIcon.vue';
import AppSwitch from '../../controls/AppSwitch.vue';
import AppSelect from '../../controls/AppSelect.vue';
import SettingRow from '../../controls/SettingRow.vue';
import AccentPresetPicker from '../../controls/AccentPresetPicker.vue';
import { computed } from 'vue';

const props = defineProps({ compact: Boolean });
const prefix = props.compact ? 'quick-' : 'settings-';
const darkMode = computed({
  get: () => effectiveColorMode.value === 'dark',
  set: (value) => {
    appearance.mode = value ? 'dark' : 'light';
  }
});
const animations = [
  {
    key: 'clickAnimations',
    label: 'Click animations',
    description:
      'Animate press feedback, ripples, switches, and disclosure controls.'
  },
  {
    key: 'hoverAnimations',
    label: 'Hover animations',
    description:
      'Animate pointer hover feedback. When disabled, hover states change instantly.'
  },
  {
    key: 'fadeAnimations',
    label: 'Fades and transitions',
    description:
      'Animate appearing content, view transitions, expansion, and other interface fades.'
  },
  {
    key: 'popupAnimations',
    label: 'Menu and popup animations',
    description: 'Animate opening and closing menus, dropdowns, and popups.'
  }
];
</script>

<template>
  <div class="appearance-settings" :class="{ 'compact-settings': compact }">
    <section :class="{ 'settings-section': !compact }">
      <header v-if="!compact">
        <h2>{{ t('Appearance') }}</h2>
        <p class="muted">
          {{
            t(
              'Choose the interface style, color mode, palettes, and semantic icon set.'
            )
          }}
        </p>
      </header>
      <div :class="{ 'configuration-group': !compact }">
        <SettingRow
          v-if="compact"
          :control-id="prefix + 'language'"
          title="Interface language"
          description="Changes application labels and help text while project-defined names remain unchanged."
          ><AppSelect
            :id="prefix + 'language'"
            v-model="appearance.language"
            :options="languages"
            label="Interface language"
            :aria-describedby="prefix + 'language-help'"
        /></SettingRow>
        <SettingRow
          v-if="!compact"
          :control-id="prefix + 'dark'"
          title="Dark color mode"
          description="Use dark surfaces and the dark palette assigned to the selected interface style."
          ><AppSwitch
            :id="prefix + 'dark'"
            v-model="darkMode"
            label="Dark color mode"
            :aria-describedby="prefix + 'dark-help'"
        /></SettingRow>
        <SettingRow
          :control-id="prefix + 'theme'"
          title="Interface style"
          :description="
            themes.find((item) => item.value === appearance.theme).description
          "
          ><AppSelect
            :id="prefix + 'theme'"
            v-model="appearance.theme"
            :options="themes"
            label="Interface style"
            :aria-describedby="prefix + 'theme-help'"
        /></SettingRow>
        <SettingRow
          v-if="compact"
          :control-id="prefix + 'mode'"
          title="Color mode"
          description="Choose light or dark surfaces, or follow the system preference."
          ><AppSelect
            :id="prefix + 'mode'"
            v-model="appearance.mode"
            :options="colorModes"
            label="Color mode"
            :aria-describedby="prefix + 'mode-help'"
        /></SettingRow>
        <template v-if="!compact">
          <SettingRow
            v-for="mode in ['light', 'dark']"
            :key="mode"
            class="appearance-palette-row"
            :control-id="prefix + mode + '-palette'"
            :title="
              mode === 'light' ? 'Light mode palette' : 'Dark mode palette'
            "
            :description="
              mode === 'light'
                ? 'Base surface and accent used when the application is in light mode.'
                : 'Base surface and accent used when the application is in dark mode.'
            "
          >
            <AccentPresetPicker
              :id="prefix + mode + '-palette'"
              v-model="appearance.themeAccents[appearance.theme][mode]"
              :options="accentPresets"
              :mode="mode"
              :label="
                t(mode === 'light' ? 'Light mode palette' : 'Dark mode palette')
              "
              :aria-describedby="prefix + mode + '-palette-help'"
            />
          </SettingRow>
        </template>
        <SettingRow
          :control-id="prefix + 'icons'"
          title="Icon set"
          :description="
            iconSets.find((item) => item.value === appearance.iconSet)
              .description
          "
          ><AppSelect
            :id="prefix + 'icons'"
            v-model="appearance.iconSet"
            :options="iconSets"
            label="Icon set"
            :aria-describedby="prefix + 'icons-help'"
        /></SettingRow>
        <SettingRow
          v-if="!compact"
          v-for="animation in animations"
          :key="animation.key"
          :control-id="prefix + animation.key"
          :title="animation.label"
          :description="animation.description"
          ><AppSwitch
            :id="prefix + animation.key"
            v-model="appearance[animation.key]"
            :label="animation.label"
            :aria-describedby="prefix + animation.key + '-help'"
        /></SettingRow>
      </div>
    </section>
    <section v-if="!compact" class="settings-section">
      <header>
        <h2>{{ t('Language') }}</h2>
        <p class="muted">
          {{ t('Choose the language used by the application interface.') }}
        </p>
      </header>
      <div class="configuration-group">
        <SettingRow
          :control-id="prefix + 'language'"
          title="Interface language"
          description="Changes application labels and help text while project-defined names remain unchanged."
          ><AppSelect
            :id="prefix + 'language'"
            v-model="appearance.language"
            :options="languages"
            label="Interface language"
            :aria-describedby="prefix + 'language-help'"
        /></SettingRow>
      </div>
    </section>
    <section v-if="!compact" class="settings-section">
      <header>
        <h2>{{ t('Browser preferences') }}</h2>
        <p class="muted">
          {{
            t(
              'Additional browser features remain available alongside the Handler layout.'
            )
          }}
        </p>
      </header>
      <div class="configuration-group">
        <SettingRow
          :control-id="prefix + 'mode'"
          title="Color mode"
          description="Choose light or dark surfaces, or follow the system preference."
          ><AppSelect
            :id="prefix + 'mode'"
            v-model="appearance.mode"
            :options="colorModes"
            label="Color mode"
            :aria-describedby="prefix + 'mode-help'"
        /></SettingRow>
        <SettingRow
          :control-id="prefix + 'discussion'"
          title="Object notes"
          description="Open object and process notes in the Task Inspector, or use a separate notes-only window."
          ><AppSelect
            :id="prefix + 'discussion'"
            v-model="appearance.discussionView"
            :options="[
              { value: 'inspector', label: 'Task Inspector' },
              { value: 'notes', label: 'Standalone notes' }
            ]"
            label="Object notes"
            :aria-describedby="prefix + 'discussion-help'"
        /></SettingRow>
        <div class="icon-preview" :aria-label="t('Icon preview')">
          <AppIcon
            v-for="name in [
              'menu',
              'edit',
              'link',
              'activity',
              'connection',
              'queue',
              'history',
              'appearance',
              'settings',
              'search',
              'add'
            ]"
            :key="name"
            :name="name"
          />
        </div>
      </div>
      <p class="muted">
        {{
          t(
            'The system reduced-motion preference takes priority over animation settings.'
          )
        }}
        {{
          t(
            'Graphics backend selection belongs to Qt. The browser controls web rendering.'
          )
        }}
      </p>
    </section>
  </div>
</template>
<style>
.configuration-native .appearance-palette-row {
  grid-template-columns: minmax(0, 1fr) min(380px, 48%);
}
</style>
