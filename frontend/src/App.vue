<script setup>
import { onMounted } from "vue";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();

onMounted(async () => {
  if (auth.token && !auth.user) {
    await auth.fetchMe().catch(() => {});
  }
});
</script>

<template>
  <router-view />
</template>
