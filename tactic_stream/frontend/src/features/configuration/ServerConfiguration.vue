<script>
import { serverConfiguration, saveServerConfiguration } from '../../api.js';
import { t } from '../../i18n.js';
import AppIcon from '../../controls/AppIcon.vue';
import AppButton from '../../controls/AppButton.vue';
import FrameSettings from './FrameSettings.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/server.ui.mjs';
import { timestampFullLabel } from '../activity/activity.js';

export default {
  components: { FrameSettings, AppIcon, AppButton },
  props: {
    ticket: { type: String, required: true },
    showDetails: Boolean,
    groupTitles: Array
  },
  emits: ['session-expired'],
  data() {
    return {
      configuration: null,
      activeGroup: 'Services and workers',
      search: '',
      loading: false,
      saving: false,
      clientsLoading: false,
      clientsError: '',
      error: '',
      errorField: null,
      notice: '',
      draft: {},
      baseline: {},
      expanded: [],
      generation: 0
    };
  },
  computed: {
    fields() {
      return UI.fields(
        {
          groups: this.groups,
          draft: this.draft,
          expanded: this.expanded,
          showDetails: this.showDetails,
          errorField: this.errorField
        },
        appearance.language
      );
    },
    frameValues() {
      const values = { ...this.draft };
      for (const group of this.groups)
        for (const setting of group.settings) {
          if (!setting.editable) values[setting.path] = this.value(setting);
          else if (setting.input_type === 'boolean')
            values[setting.path] = this.booleanValue(setting);
          if (setting.services)
            for (const service of setting.services)
              values[setting.path + '#' + service.name] = this.serviceEnabled(
                setting,
                service
              );
        }
      for (const field of this.fields)
        if (field.detailsText) values[field.field] = field.detailsText;
      return values;
    },
    changes() {
      return Object.fromEntries(
        Object.entries(this.draft).filter(
          ([path, value]) => value !== this.baseline[path]
        )
      );
    },
    hasChanges() {
      return Object.keys(this.changes).length > 0;
    },
    failedSetting() {
      return this.configuration?.groups
        .flatMap((group) => group.settings)
        .find((setting) => setting.path === this.errorField)?.label;
    },
    groups() {
      const query = this.search.trim().toLowerCase();
      return (this.configuration?.groups || [])
        .filter(
          (group) => !this.groupTitles || this.groupTitles.includes(group.title)
        )
        .filter((group) => query || group.title === this.activeGroup)
        .map((group) => ({
          ...group,
          settings: group.settings.filter((setting) =>
            [
              setting.path,
              t(setting.label),
              t(setting.description),
              t(group.title)
            ].some((value) => value.toLowerCase().includes(query))
          )
        }))
        .filter((group) => group.settings.length);
    }
  },
  watch: {
    ticket() {
      this.generation++;
      this.configuration = null;
      this.draft = {};
      this.baseline = {};
      this.expanded = [];
      this.loading = this.saving = this.clientsLoading = false;
      this.error = this.notice = this.clientsError = '';
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
    this.load();
  },
  beforeUnmount() {
    this.generation++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    fieldEdited(action) {
      const setting = this.configuration.groups
        .flatMap((group) => group.settings)
        .find((setting) => setting.path === action.field);
      const value =
        setting.input_type === 'boolean'
          ? action.value
            ? 'true'
            : 'false'
          : setting.secret && !action.value
            ? null
            : action.value;
      this.editSetting(action.field, value);
    },
    action(action) {
      if (action.type === 'details')
        this.expanded = this.expanded.includes(action.path)
          ? this.expanded.filter((path) => path !== action.path)
          : [...this.expanded, action.path];
      else if (action.type === 'default' || action.type === 'clear')
        this.editSetting(action.path, '');
      else if (action.type === 'service') {
        const setting = this.configuration.groups
          .flatMap((group) => group.settings)
          .find((setting) => setting.path === action.path);
        this.editService(setting, action.name, action.value);
      }
    },
    groupHeading(title) {
      return (
        {
          'Services and workers': 'Processes and monitoring',
          Network: 'Connection',
          Database: 'Database connection',
          'File repository': 'Repository locations',
          'Task scheduling': 'Schedule',
          Security: 'Account and API security',
          'Directories and logs': 'Runtime paths'
        }[title] || title
      );
    },
    groupChanged(group) {
      return group.settings.some((setting) =>
        Object.hasOwn(this.changes, setting.path)
      );
    },
    beforeUnload(event) {
      if (!this.hasChanges && !this.saving) return;
      event.preventDefault();
      event.returnValue = '';
    },
    async load() {
      if (this.loading || this.saving || this.hasChanges) return;
      const generation = this.generation;
      this.loading = true;
      this.error = '';
      this.notice = '';
      try {
        const configuration = await serverConfiguration(this.ticket);
        if (generation !== this.generation) return;
        this.configuration = configuration;
        this.resetDraft();
      } catch (error) {
        if (generation !== this.generation) return;
        if (error.code === 'authentication_failed')
          this.$emit('session-expired');
        this.error =
          error instanceof TypeError
            ? 'Unable to reach the server.'
            : error.message;
      } finally {
        if (generation === this.generation) this.loading = false;
      }
    },
    resetDraft(groupTitles) {
      const previous = { ...this.draft };
      this.draft = {};
      for (const group of this.configuration.groups) {
        for (const setting of group.settings) {
          if (!setting.editable) continue;
          this.draft[setting.path] =
            setting.input_type === 'services'
              ? setting.services
                  .filter((service) => service.enabled)
                  .map((service) => service.name)
                  .join('|')
              : setting.secret
                ? null
                : (setting.value ?? '');
        }
      }
      this.baseline = { ...this.draft };
      if (groupTitles)
        for (const group of this.configuration.groups)
          if (!groupTitles.includes(group.title)) {
            for (const setting of group.settings)
              if (Object.hasOwn(previous, setting.path))
                this.draft[setting.path] = previous[setting.path];
          }
      this.error = '';
      this.errorField = null;
    },
    async refreshClients() {
      if (this.clientsLoading || this.loading || this.saving) return;
      const generation = this.generation;
      this.clientsLoading = true;
      this.clientsError = '';
      try {
        const result = await serverConfiguration(this.ticket);
        if (generation !== this.generation) return;
        this.configuration.event_clients = result.event_clients;
      } catch (error) {
        if (generation !== this.generation) return;
        if (error.code === 'authentication_failed')
          this.$emit('session-expired');
        this.clientsError =
          error instanceof TypeError
            ? 'Unable to reach the server.'
            : error.message;
      } finally {
        if (generation === this.generation) this.clientsLoading = false;
      }
    },
    connectedTime(value) {
      return timestampFullLabel(new Date(value).toISOString());
    },
    async save(groupTitles) {
      if (this.loading || this.saving) return false;
      const generation = this.generation;
      const changes = Object.fromEntries(
        Object.entries(this.changes).filter(
          ([path]) =>
            !groupTitles ||
            this.configuration.groups.some(
              (group) =>
                groupTitles.includes(group.title) &&
                group.settings.some((setting) => setting.path === path)
            )
        )
      );
      if (!Object.keys(changes).length) return true;
      const pending = { ...this.changes };
      this.saving = true;
      this.error = '';
      this.errorField = null;
      try {
        const configuration = await saveServerConfiguration(
          this.ticket,
          changes,
          this.configuration.revision
        );
        if (generation !== this.generation) return false;
        this.configuration = configuration;
        this.resetDraft();
        for (const [path, value] of Object.entries(pending))
          if (!Object.hasOwn(changes, path)) this.draft[path] = value;
        this.notice = this.configuration.restart_required
          ? 'Saved to XML. Restart the backend to apply these settings.'
          : this.configuration.saved
            ? 'Saved to XML. New requests use the updated settings.'
            : 'No configuration changes were needed.';
        return true;
      } catch (error) {
        if (generation !== this.generation) return false;
        if (error.code === 'authentication_failed')
          this.$emit('session-expired');
        this.error =
          error instanceof TypeError
            ? 'Unable to reach the server.'
            : error.message;
        this.errorField = error.field;
        const group = this.configuration.groups.find((group) =>
          group.settings.some((setting) => setting.path === error.field)
        );
        if (group) {
          this.activeGroup = group.title;
          this.search = '';
        }
        return false;
      } finally {
        if (generation === this.generation) this.saving = false;
      }
    },
    booleanValue(setting) {
      return (this.draft[setting.path] || setting.default) === 'true';
    },
    value(setting) {
      if (setting.secret)
        return t(setting.configured ? 'Configured (hidden)' : 'Not set');
      return setting.value ?? t('Not set');
    },
    serviceEnabled(setting, service) {
      return setting.editable
        ? this.draft[setting.path].split('|').includes(service.name)
        : service.enabled;
    },
    editService(setting, name, enabled) {
      const services = new Set(this.draft[setting.path].split('|'));
      if (enabled) services.add(name);
      else services.delete(name);
      this.editSetting(
        setting.path,
        ['tactic', 'queue', 'files']
          .filter((service) => services.has(service))
          .join('|')
      );
    },
    editSetting(path, value) {
      this.draft[path] = value;
      if (this.errorField === path) {
        this.error = '';
        this.errorField = null;
      }
    }
  }
};
</script>

<template>
  <section class="content server-configuration" :aria-busy="loading || saving">
    <p v-if="error" class="error" role="alert">
      <strong v-if="failedSetting">{{ t(failedSetting) }}: </strong
      >{{ t(error) }}
    </p>
    <p v-if="notice && !hasChanges" class="notice" role="status">
      {{ t(notice) }}
    </p>
    <p v-if="loading" class="muted" role="status">{{ t('Loading data…') }}</p>
    <template v-if="configuration">
      <section
        v-if="activeGroup === 'Services and workers' && !search"
        class="settings-section event-clients"
      >
        <header>
          <h2>
            {{ t('SSE connections') }} ·
            {{ configuration.event_clients?.length || 0 }}
          </h2>
          <AppButton
            icon="refresh"
            label="Refresh connections"
            :disabled="clientsLoading || loading || saving"
            @click="refreshClients"
          />
        </header>
        <p class="muted">
          {{
            t(
              'Open SSE connections across all web workers. This is a connection list, not user presence. Refresh to update the snapshot; closed connections disappear within the collection interval, crashed workers within 45 seconds.'
            )
          }}
        </p>
        <p v-if="clientsError" class="error" role="alert">
          {{ t(clientsError) }}
        </p>
        <div class="event-clients-scroll">
          <table v-if="configuration.event_clients?.length">
            <thead>
              <tr>
                <th>{{ t('User') }}</th>
                <th>{{ t('Project') }}</th>
                <th>{{ t('Client') }}</th>
                <th>{{ t('Address') }}</th>
                <th>{{ t('Connected at') }}</th>
                <th>{{ t('Worker') }}</th>
                <th>{{ t('Subscriptions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="client in configuration.event_clients"
                :key="client.connection"
              >
                <td>{{ client.login }}</td>
                <td>{{ client.project }}</td>
                <td>{{ t(client.application) }}</td>
                <td>{{ client.address }}</td>
                <td>{{ connectedTime(client.connected_at) }}</td>
                <td>{{ client.worker }}</td>
                <td>
                  <details>
                    <summary>
                      {{ client.channels.join(', ') }} ·
                      {{ client.search_types.length }}
                    </summary>
                    <code>{{ client.search_types.join('\n') }}</code>
                  </details>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">{{ t('No open SSE connections') }}</p>
        </div>
      </section>
      <details v-if="showDetails" class="configuration-source">
        <summary>{{ t('Configuration source') }}</summary>
        <button :disabled="loading || saving || hasChanges" @click="load">
          <AppIcon name="refresh" />{{ t('Refresh') }}
        </button>
        <span class="muted">{{ t('Configuration file') }}</span
        ><code>{{ configuration.config_path }}</code>
        <span class="muted">{{ t('Data directory') }}</span
        ><code>{{ configuration.data_dir }}</code>
        <p class="muted">
          {{
            t(
              'Supported settings can be saved to XML. Values come from the configuration file; startup overrides may differ.'
            )
          }}
        </p>
        <p v-if="!configuration.writable" class="muted">
          {{
            t(
              'The configuration file is missing or not writable. Editing is unavailable.'
            )
          }}
        </p>
      </details>
      <div class="configuration-groups">
        <FrameSettings
          :fields="fields"
          :values="frameValues"
          :busy="loading || saving"
          natural
          @field="fieldEdited"
          @action="action"
        />
        <p v-if="!groups.length" class="muted">{{ t('No settings found') }}</p>
        <details
          v-if="configuration.undocumented.length"
          class="configuration-group"
        >
          <summary>
            {{ t('Other configured options') }} ·
            {{ configuration.undocumented.length }}
          </summary>
          <p class="muted">
            {{
              t(
                'These options still need documentation and a support check. Their values are not exposed.'
              )
            }}
          </p>
          <ul>
            <li v-for="path in configuration.undocumented" :key="path">
              <code>{{ path }}</code>
            </li>
          </ul>
        </details>
      </div>
    </template>
  </section>
</template>

<style>
.event-clients > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.event-clients-scroll {
  max-height: 320px;
  overflow: auto;
  scrollbar-gutter: stable;
}
.event-clients-scroll table {
  width: 100%;
}
.event-clients-scroll th,
.event-clients-scroll td {
  text-align: left;
  padding: 8px;
  white-space: nowrap;
}
.event-clients-scroll code {
  white-space: pre;
  display: block;
}
</style>
