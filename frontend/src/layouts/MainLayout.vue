<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();

const menu = computed(() => {
  const items = [
    { index: "/calendar", label: "我的週曆", icon: "📅" },
    { index: "/reports", label: "報表", icon: "📊" },
  ];
  if (auth.isManager || auth.isAdmin) {
    items.splice(1, 0, {
      index: "/team",
      label: auth.isAdmin ? "全員週曆" : "部門週曆",
      icon: "👥",
    });
  }
  if (auth.isAdmin) {
    items.push(
      { index: "/admin/projects", label: "專案管理", icon: "📂" },
      { index: "/admin/users", label: "員工管理", icon: "🧑" },
      { index: "/admin/departments", label: "部門管理", icon: "🏢" },
      { index: "/admin/categories", label: "個人類別", icon: "🏷" },
      { index: "/admin/title-presets", label: "標題預設", icon: "🏷" },
      { index: "/admin/audit", label: "安全稽核", icon: "🛡" }
    );
  }
  return items;
});

const roleLabel = computed(() => {
  return (
    {
      admin: "管理者",
      manager: "主管",
      employee: "員工",
    }[auth.role] || ""
  );
});

async function logout() {
  await auth.logout();
  router.push("/login");
}

function handleSelect(index) {
  router.push(index);
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">工作日誌</div>
      <el-menu
        :default-active="$route.path"
        class="side-menu"
        @select="handleSelect"
      >
        <el-menu-item v-for="m in menu" :key="m.index" :index="m.index">
          <span style="margin-right: 8px">{{ m.icon }}</span>
          {{ m.label }}
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div></div>
        <el-dropdown>
          <span class="user-info">
            <el-avatar :size="32" style="margin-right: 8px">{{
              auth.user?.full_name?.slice(0, 1) || "U"
            }}</el-avatar>
            {{ auth.user?.full_name }}
            <el-tag size="small" style="margin-left: 8px">{{
              roleLabel
            }}</el-tag>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="logout">登出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  background: #001529;
  color: #fff;
}
.brand {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 2px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.side-menu {
  border-right: none;
  background: transparent;
}
.side-menu :deep(.el-menu-item) {
  color: #cfd8dc;
}
.side-menu :deep(.el-menu-item.is-active) {
  background: #1890ff;
  color: #fff;
}
.side-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}
.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.el-main {
  background: #f5f7fa;
  padding: 0;
}
</style>
