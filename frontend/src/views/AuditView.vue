<script setup>
import { onMounted, reactive, ref } from "vue";
import { auditApi } from "../api";

const rows = ref([]);
const total = ref(0);
const loading = ref(false);

const filters = reactive({
  action: "",
  actor_id: null,
  target_type: "",
  target_id: null,
  from: null,
  to: null,
  page: 1,
  per_page: 50,
});

// 常見 action group 快選
const actionGroups = [
  { label: "全部", value: "" },
  { label: "登入相關", value: "auth.*" },
  { label: "使用者管理", value: "users.*" },
  { label: "薪資異動", value: "users.rate_changed" },
  { label: "角色變更", value: "users.role_changed" },
  { label: "代他人記錄", value: "entries.create_for_other,entries.update_other,entries.delete_other" },
  { label: "檢視他人工時", value: "reports.view_user_hours_other,entries.view_others" },
  { label: "檢視部門報表", value: "reports.view_department_summary" },
  { label: "檢視專案成本", value: "reports.view_project_cost" },
  { label: "專案管理", value: "projects.*" },
  { label: "部門管理", value: "departments.*" },
  { label: "類別管理", value: "categories.*" },
];

async function load() {
  loading.value = true;
  try {
    const params = {};
    if (filters.action) params.action = filters.action;
    if (filters.actor_id) params.actor_id = filters.actor_id;
    if (filters.target_type) params.target_type = filters.target_type;
    if (filters.target_id) params.target_id = filters.target_id;
    if (filters.from) params.from = filters.from;
    if (filters.to) params.to = filters.to;
    params.page = filters.page;
    params.per_page = filters.per_page;
    const data = await auditApi.list(params);
    rows.value = data.rows;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

function onPageChange(p) {
  filters.page = p;
  load();
}

function onFilterChange() {
  filters.page = 1;
  load();
}

function fmt(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

const actionColor = {
  "auth.login_success": "success",
  "auth.login_failed": "danger",
  "auth.logout": "info",
  "auth.refresh": "info",
  "users.create": "success",
  "users.update": "",
  "users.role_changed": "warning",
  "users.rate_changed": "warning",
  "users.deactivated": "danger",
  "entries.create_for_other": "warning",
  "entries.update_other": "warning",
  "entries.delete_other": "danger",
  "entries.view_others": "info",
  "reports.view_user_hours_other": "info",
  "reports.view_department_summary": "info",
  "reports.view_project_cost": "info",
};

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>安全稽核</h2>
    </div>
    <div class="card">
      <div class="filters">
        <el-select
          v-model="filters.action"
          placeholder="事件類型"
          clearable
          style="width: 200px"
          @change="onFilterChange"
        >
          <el-option
            v-for="g in actionGroups"
            :key="g.value"
            :label="g.label"
            :value="g.value"
          />
        </el-select>
        <el-input
          v-model.number="filters.actor_id"
          placeholder="操作者 ID"
          clearable
          style="width: 130px; margin-left: 8px"
          @change="onFilterChange"
        />
        <el-input
          v-model="filters.target_type"
          placeholder="目標類型 (user/entry...)"
          clearable
          style="width: 180px; margin-left: 8px"
          @change="onFilterChange"
        />
        <el-input
          v-model.number="filters.target_id"
          placeholder="目標 ID"
          clearable
          style="width: 120px; margin-left: 8px"
          @change="onFilterChange"
        />
        <el-date-picker
          v-model="filters.from"
          type="datetime"
          placeholder="起"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 200px; margin-left: 8px"
          @change="onFilterChange"
        />
        <el-date-picker
          v-model="filters.to"
          type="datetime"
          placeholder="迄"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 200px; margin-left: 8px"
          @change="onFilterChange"
        />
        <el-button style="margin-left: 8px" @click="load">重新整理</el-button>
      </div>

      <el-table
        :data="rows"
        v-loading="loading"
        stripe
        style="margin-top: 12px"
        row-key="id"
      >
        <el-table-column label="時間" width="170">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作者" width="160">
          <template #default="{ row }">
            <div>{{ row.actor_name || "-" }}</div>
            <div class="sub">{{ row.actor_username }}</div>
          </template>
        </el-table-column>
        <el-table-column label="事件" width="230">
          <template #default="{ row }">
            <el-tag :type="actionColor[row.action] || ''" size="small">
              {{ row.action }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="目標" width="180">
          <template #default="{ row }">
            <template v-if="row.target_type">
              {{ row.target_type }} #{{ row.target_id ?? "-" }}
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="詳情" min-width="280">
          <template #default="{ row }">
            <pre class="meta">{{ JSON.stringify(row.meta, null, 0) }}</pre>
          </template>
        </el-table-column>
        <el-table-column label="IP" width="130" prop="ip" />
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="filters.page"
          :page-size="filters.per_page"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="onPageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 0;
}
.sub {
  color: #909399;
  font-size: 12px;
}
.meta {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
}
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
