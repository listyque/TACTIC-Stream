<script setup>
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { t } from '../../i18n.js'
defineProps({ reference: Object, users: Array, forwarded: Boolean, dismissible: Boolean })
defineEmits(['activate', 'dismiss'])
</script>
<template>
  <component :is="!dismissible && reference.available ? AppButton : 'div'" class="message-reference" :class="{ forwarded, unavailable: !reference.available }" @click="!dismissible && reference.available && $emit('activate')">
    <AppIcon :name="forwarded ? 'MDI_SHARE' : 'MDI_REPLY'" />
    <span class="message-reference-text">
      <strong>{{ reference.available ? t(forwarded ? 'Forwarded from {name}' : 'Reply to {name}', { name: users?.find(user => user.login === reference.sender)?.displayName || reference.sender || t('Unknown user') }) : t(forwarded ? 'Forwarded message unavailable' : 'Original message is unavailable') }}</strong>
      <span v-if="reference.available && reference.body">{{ reference.body }}</span>
      <small v-if="forwarded && reference.available && reference.attachments?.length">{{ t('{count} attachments', { count: reference.attachments.length }) }}</small>
    </span>
    <AppButton v-if="dismissible" icon-only icon="close" label="Cancel reply" @click.stop="$emit('dismiss')" />
  </component>
</template>
