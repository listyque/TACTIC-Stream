import { createApp, h, reactive, markRaw } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import ItemPreview from '../../frontend/src/controls/ItemPreview.vue';
import CodeBlock from '../../frontend/src/controls/CodeBlock.vue';
import DocumentPane from '../../frontend/src/controls/DocumentPane.vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import * as Debug from '../../src/tactic_stream/shared_ui/features/support/diagnostics/debug.ui.mjs';
import * as Performance from '../../src/tactic_stream/shared_ui/features/support/diagnostics/performance.ui.mjs';
import * as Profile from '../../src/tactic_stream/shared_ui/features/support/identity/profile.ui.mjs';
import * as Editor from '../../src/tactic_stream/shared_ui/features/support/identity/profile.editor.ui.mjs';
import * as SignIn from '../../src/tactic_stream/shared_ui/features/support/connection/sign_in.ui.mjs';
import * as Presets from '../../src/tactic_stream/shared_ui/features/support/connection/presets.ui.mjs';
import * as Updates from '../../src/tactic_stream/shared_ui/features/support/connection/updates.ui.mjs';
import * as ErrorUI from '../../src/tactic_stream/shared_ui/features/support/feedback/error.ui.mjs';
import { t } from '../../frontend/src/i18n.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';

const modules = {
  debug: Debug,
  performance: Performance,
  profile: Profile,
  editor: Editor,
  sign_in: SignIn,
  presets: Presets,
  updates: Updates,
  error: ErrorUI
};
const state = reactive({
  screen: 'performance',
  model: { summary: { count: 0 } },
  models: {
    samples: [],
    events: [],
    groups: [],
    users: [],
    presets: [],
    releases: []
  },
  width: 1100,
  height: 740,
  language: 'en',
  changelog: '',
  currentVersion: '',
  command: ''
});
Object.assign(appearance, {
  mode: 'dark',
  theme: 'md3',
  language: 'en',
  clickAnimations: false,
  hoverAnimations: false,
  popupAnimations: false,
  fadeAnimations: false
});
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
const emptyView = markRaw({ render: () => h('div') });
const versionView = markRaw({
  render: () =>
    h(
      'span',
      {
        style: {
          display: 'block',
          height: '100%',
          fontSize: '12px',
          color: 'var(--muted)'
        }
      },
      t('Current version  ') + state.currentVersion
    )
});
const preview = markRaw(ItemPreview),
  code = markRaw(CodeBlock),
  document = markRaw(DocumentPane);
window.support = {
  events: [],
  configure(record) {
    Object.assign(state, structuredClone(record));
    Object.assign(appearance, {
      mode: record.dark ? 'dark' : 'light',
      theme: record.style,
      language: record.language
    });
    this.events = [];
  },
  state
};
createApp({
  setup() {
    function row(list, record) {
      const width = list.width - 16;
      if (state.screen === 'debug')
        return Debug.row(state.model, list, record, width, state.language);
      if (state.screen === 'performance')
        return Performance.row(state.model, record, width, state.language);
      if (state.screen === 'profile')
        return Profile.userRow(state.model, record, width, state.language);
      if (state.screen === 'editor')
        return Editor.groupRow(state.model, record, width, state.language);
      if (state.screen === 'presets')
        return Presets.row(record, width, state.language);
      if (state.screen === 'updates') return Updates.row(record, width);
      throw Error('Unexpected support row: ' + state.screen);
    }
    return () => {
      const model = state.model;
      const views = {
        avatar: {
          component: preview,
          props: {
            source: '',
            fallbackText: model.creating ? '?' : 'AA',
            accent: '#ad4242',
            previewSize: 54,
            round: true,
            outlined: true
          }
        },
        activity: { component: emptyView },
        version: { component: versionView },
        changelog: {
          component: document,
          props: {
            text: state.changelog,
            documentKey: 'changelog',
            presented: true
          }
        },
        requests: { component: code, props: { code: state.command } }
      };
      return h(
        'section',
        {
          id: 'support',
          style: {
            position: 'relative',
            width: state.width + 'px',
            height: state.height + 'px',
            background: 'var(--page)',
            overflow: 'hidden'
          }
        },
        [
          h(FrameView, {
            scene: modules[state.screen].describe(
              model,
              state.width,
              state.height,
              state.language
            ),
            models: state.models,
            views,
            describeRow: row,
            onEvent: (action) => window.support.events.push(action)
          })
        ]
      );
    };
  }
}).mount('#app');
