<script setup>
import ItemPreview from './ItemPreview.vue';
import AppIcon from './AppIcon.vue';
import { t } from '../i18n.js';
defineProps({
  login: String,
  displayName: String,
  initials: String,
  avatarUrl: String,
  avatarColor: String,
  retired: Boolean,
  avatarSize: { type: Number, default: 40 },
  emphasized: Boolean
});
</script>

<template>
  <span
    class="user-identity"
    :class="{ retired, emphasized }"
    :style="{ '--avatar-size': avatarSize + 'px' }"
    ><ItemPreview
      :source="avatarUrl"
      :fallback-text="initials"
      fallback-icon="person"
      :accent="avatarColor"
      :preview-size="avatarSize"
      round
      outlined
    /><span class="user-identity-text"
      ><strong>{{ displayName || login }}</strong
      ><small v-if="login && displayName !== login" class="muted">{{
        login
      }}</small></span
    ><span v-if="retired" class="muted identity-retired"
      ><AppIcon name="archive" />{{ t('Retired') }}</span
    ></span
  >
</template>
<style>
.user-identity {
  display: flex;
  align-items: center;
  gap: var(--identity-spacing);
  min-width: 0;
  flex: 1;
}
.user-identity.retired {
  opacity: 0.5;
}
.user-identity .image-picker-preview {
  width: var(--avatar-size);
  height: var(--avatar-size);
  flex: 0 0 var(--avatar-size);
}
.user-identity-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
  gap: var(--identity-text-spacing);
}
.user-identity-text > * {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.user-identity-text > strong {
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
  font-weight: 600;
}
.user-identity.emphasized .user-identity-text > strong {
  font-size: var(--font-body-large-size);
  line-height: var(--font-body-large-line-height);
}
.user-identity-text > small {
  font-size: var(--font-secondary-size);
  line-height: var(--font-secondary-line-height);
}
.user-identity .identity-retired {
  display: inline-flex;
  align-items: center;
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
}
</style>
