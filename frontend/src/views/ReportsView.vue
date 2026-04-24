<script setup>
import { computed, onMounted, ref, watch } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";

import { departmentsApi, entriesApi, reportsApi, usersApi } from "../api";
import { useAuthStore } from "../stores/auth";

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
]);

const auth = useAuthStore();

const month = ref(new Date().toISOString().slice(0, 7)); // yyyy-mm
const users = ref([]);
const departments = ref([]);
const selectedUserId = ref(null);
const selectedDeptId = ref(null);

const projectCost = ref([]);
const userHours = ref(null);
const deptSummary = ref(null);

const canSeeProjectCost = computed(() => auth.isAdmin || auth.isManager);
const canSeeDeptSummary = computed(() => auth.isAdmin || auth.isManager);
const canSeeCost = computed(() => auth.isAdmin);

// ---------- drill-down state ----------
const drill = ref({
  visible: false,
  loading: false,
  title: "",
  subtitle: "",
  rows: [],
  showUserColumn: false,
});

function monthRangeIso(ym) {
  const [y, m] = ym.split("-").map((x) => parseInt(x, 10));
  const pad = (n) => String(n).padStart(2, "0");
  const lastDay = new Date(y, m, 0).getDate();
  // 送 naive local ISO，後端 TimeEntry 也以 naive 儲存
  return {
    from: `${y}-${pad(m)}-01T00:00:00`,
    to: `${y}-${pad(m)}-${pad(lastDay)}T23:59:59`,
  };
}

function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

async function openDrillDown({ title, subtitle, params, showUserColumn }) {
  drill.value.visible = true;
  drill.value.loading = true;
  drill.value.title = title;
  drill.value.subtitle = subtitle || "";
  drill.value.showUserColumn = !!showUserColumn;
  drill.value.rows = [];
  try {
    const rows = await entriesApi.list(params);
    drill.value.rows = rows;
  } finally {
    drill.value.loading = false;
  }
}

// ---------- loaders ----------
async function loadProjectCost() {
  if (!canSeeProjectCost.value) return;
  projectCost.value = await reportsApi.projectCost();
}

async function loadUserHours() {
  const uid = selectedUserId.value || auth.user?.id;
  if (!uid) return;
  userHours.value = await reportsApi.userHours({
    user_id: uid,
    month: month.value,
  });
}

async function loadDeptSummary() {
  if (!canSeeDeptSummary.value) return;
  const params = { month: month.value };
  if (auth.isAdmin && selectedDeptId.value) {
    params.dept_id = selectedDeptId.value;
  }
  deptSummary.value = await reportsApi.departmentSummary(params);
}

// ---------- chart options ----------
const projectCostOption = computed(() => {
  const rows = projectCost.value || [];
  const series = [
    {
      name: "預算",
      type: "bar",
      data: rows.map((r) => r.budget),
      itemStyle: { color: "#91cc75" },
    },
  ];
  if (canSeeCost.value) {
    series.push({
      name: "實際成本",
      type: "bar",
      data: rows.map((r) => r.cost ?? 0),
      itemStyle: { color: "#ee6666" },
    });
  }
  return {
    title: {
      text: canSeeCost.value ? "專案成本 vs 預算" : "專案預算",
      subtext: "點擊柱狀圖可檢視該專案明細",
      left: "center",
      subtextStyle: { fontSize: 11, color: "#909399" },
    },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { bottom: 0 },
    grid: { top: 70, left: 50, right: 30, bottom: 50 },
    xAxis: {
      type: "category",
      data: rows.map((r) => r.code),
      axisLabel: { interval: 0, rotate: 30 },
    },
    yAxis: { type: "value", axisLabel: { formatter: "{value}" } },
    series,
  };
});

const userHoursPieOption = computed(() => {
  if (!userHours.value) return {};
  const data = [
    ...userHours.value.projects.map((p) => ({
      name: p.name,
      value: p.hours,
      itemStyle: { color: p.color },
      _kind: "project",
      _id: p.project_id,
    })),
    ...userHours.value.categories.map((c) => ({
      name: c.name,
      value: c.hours,
      itemStyle: { color: c.color },
      _kind: "category",
      _id: c.category_id,
    })),
    ...(userHours.value.change_requests || []).map((cr) => ({
      name: cr.title,
      value: cr.hours,
      itemStyle: { color: cr.color },
      _kind: "change_request",
      _id: cr.change_request_id,
    })),
  ];
  return {
    title: {
      text: "個人工時分布",
      subtext: "點擊區塊可檢視該項明細",
      left: "center",
      subtextStyle: { fontSize: 11, color: "#909399" },
    },
    tooltip: { trigger: "item", formatter: "{b}: {c} 小時 ({d}%)" },
    legend: { bottom: 0, type: "scroll" },
    series: [
      {
        type: "pie",
        radius: ["40%", "65%"],
        center: ["50%", "52%"],
        data,
        label: { formatter: "{b}\n{c}h" },
      },
    ],
  };
});

const deptBarOption = computed(() => {
  if (!deptSummary.value) return {};
  const rows = deptSummary.value.rows || [];
  const yAxis = [
    { type: "value", name: "工時", axisLabel: { formatter: "{value} h" } },
  ];
  const series = [
    {
      name: "工時",
      type: "bar",
      data: rows.map((r) => r.hours),
      itemStyle: { color: "#5470c6" },
    },
  ];
  if (canSeeCost.value) {
    yAxis.push({
      type: "value",
      name: "成本",
      axisLabel: { formatter: "{value}" },
    });
    series.push({
      name: "成本",
      type: "bar",
      yAxisIndex: 1,
      data: rows.map((r) => r.cost ?? 0),
      itemStyle: { color: "#fac858" },
    });
  }
  return {
    title: {
      text: canSeeCost.value ? "部門成員月工時 / 人力成本" : "部門成員月工時",
      subtext: "點擊柱狀圖可檢視該成員明細",
      left: "center",
      subtextStyle: { fontSize: 11, color: "#909399" },
    },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { bottom: 0 },
    grid: { top: 70, left: 60, right: 60, bottom: 60 },
    xAxis: { type: "category", data: rows.map((r) => r.full_name) },
    yAxis,
    series,
  };
});

// ---------- click handlers ----------
function onProjectCostClick(params) {
  const row = (projectCost.value || [])[params.dataIndex];
  if (!row) return;
  const { from, to } = monthRangeIso(month.value);
  openDrillDown({
    title: `${row.code} · ${row.name}`,
    subtitle: `${month.value} 的工時紀錄`,
    params: {
      project_id: row.project_id,
      from,
      to,
      scope: "team", // admin / manager 用 team 拿該月該專案的全部紀錄
    },
    showUserColumn: true,
  });
}

function onUserHoursPieClick(params) {
  const item = params.data || {};
  const uid = selectedUserId.value || auth.user?.id;
  if (!uid) return;
  const { from, to } = monthRangeIso(month.value);
  const reqParams = { user_id: uid, from, to };
  if (item._kind === "project") reqParams.project_id = item._id;
  if (item._kind === "category") reqParams.category_id = item._id;
  if (item._kind === "change_request")
    reqParams.change_request_id = item._id;
  const u = users.value.find((x) => x.id === uid) || auth.user;
  const kindLabel =
    item._kind === "project"
      ? "專案"
      : item._kind === "change_request"
        ? "需求單"
        : "類別";
  openDrillDown({
    title: `${u?.full_name || "-"} · ${item.name}`,
    subtitle: `${month.value} 的 ${kindLabel}明細`,
    params: reqParams,
    showUserColumn: false,
  });
}

function onDeptBarClick(params) {
  const rows = (deptSummary.value && deptSummary.value.rows) || [];
  const row = rows[params.dataIndex];
  if (!row) return;
  const { from, to } = monthRangeIso(month.value);
  openDrillDown({
    title: row.full_name,
    subtitle: `${row.department_name || ""} · ${month.value} 工時明細`,
    params: { user_id: row.user_id, from, to },
    showUserColumn: false,
  });
}

function onDeptRowClick(row) {
  const { from, to } = monthRangeIso(month.value);
  openDrillDown({
    title: row.full_name,
    subtitle: `${row.department_name || ""} · ${month.value} 工時明細`,
    params: { user_id: row.user_id, from, to },
    showUserColumn: false,
  });
}

function onProjectRowClick(row) {
  const { from, to } = monthRangeIso(month.value);
  openDrillDown({
    title: `${row.code} · ${row.name}`,
    subtitle: `${month.value} 的工時紀錄`,
    params: { project_id: row.project_id, from, to, scope: "team" },
    showUserColumn: true,
  });
}

watch([month, selectedUserId, selectedDeptId], () => {
  loadProjectCost();
  loadUserHours();
  loadDeptSummary();
});

onMounted(async () => {
  try {
    if (auth.isAdmin || auth.isManager) {
      users.value = await usersApi.list();
      departments.value = await departmentsApi.list();
    }
    selectedUserId.value = auth.user?.id || null;
  } catch (_) {}
  loadProjectCost();
  loadUserHours();
  loadDeptSummary();
});

const drillTotalHours = computed(() =>
  (drill.value.rows || []).reduce((s, r) => s + (r.hours || 0), 0).toFixed(2)
);
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>報表</h2>
      <div class="filters">
        <el-date-picker
          v-model="month"
          type="month"
          value-format="YYYY-MM"
          format="YYYY-MM"
          :clearable="false"
          style="width: 140px"
        />
        <el-select
          v-if="auth.isAdmin || auth.isManager"
          v-model="selectedUserId"
          placeholder="選擇員工"
          clearable
          filterable
          style="width: 200px; margin-left: 8px"
        >
          <el-option
            v-for="u in users"
            :key="u.id"
            :label="`${u.full_name}`"
            :value="u.id"
          />
        </el-select>
        <el-select
          v-if="auth.isAdmin"
          v-model="selectedDeptId"
          placeholder="所有部門"
          clearable
          style="width: 160px; margin-left: 8px"
        >
          <el-option
            v-for="d in departments"
            :key="d.id"
            :label="d.name"
            :value="d.id"
          />
        </el-select>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="canSeeProjectCost ? 12 : 24">
        <div class="card chart-card">
          <div v-if="userHours" class="summary">
            <el-statistic
              title="月總工時"
              :value="userHours.total_hours"
              suffix="h"
            />
            <el-statistic
              v-if="canSeeCost && userHours.total_cost !== undefined"
              title="月人力成本"
              :value="userHours.total_cost"
              :precision="0"
              suffix="元"
              style="margin-left: 24px"
            />
          </div>
          <v-chart
            :option="userHoursPieOption"
            style="height: 400px; cursor: pointer"
            autoresize
            @click="onUserHoursPieClick"
          />
        </div>
      </el-col>
      <el-col v-if="canSeeProjectCost" :span="12">
        <div class="card chart-card">
          <v-chart
            :option="projectCostOption"
            style="height: 440px; cursor: pointer"
            autoresize
            @click="onProjectCostClick"
          />
        </div>
      </el-col>
    </el-row>

    <div
      v-if="canSeeDeptSummary && deptSummary"
      class="card chart-card"
      style="margin-top: 16px"
    >
      <div class="summary">
        <el-statistic
          title="部門總工時"
          :value="deptSummary.total_hours"
          suffix="h"
        />
        <el-statistic
          v-if="canSeeCost && deptSummary.total_cost !== undefined"
          title="部門總成本"
          :value="deptSummary.total_cost"
          :precision="0"
          suffix="元"
          style="margin-left: 24px"
        />
      </div>
      <v-chart
        :option="deptBarOption"
        style="height: 400px; cursor: pointer"
        autoresize
        @click="onDeptBarClick"
      />

      <el-table
        :data="deptSummary.rows"
        stripe
        style="margin-top: 12px"
        @row-click="onDeptRowClick"
      >
        <el-table-column label="員工" prop="full_name" />
        <el-table-column label="部門" prop="department_name" />
        <el-table-column label="工時" prop="hours" width="120">
          <template #default="{ row }">{{ row.hours }} h</template>
        </el-table-column>
        <el-table-column
          v-if="canSeeCost"
          label="人力成本"
          prop="cost"
          width="160"
        >
          <template #default="{ row }"
            >NT$ {{ (row.cost ?? 0).toLocaleString() }}</template
          >
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default>
            <el-button type="primary" link>明細</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div
      v-if="canSeeProjectCost && projectCost.length"
      class="card chart-card"
      style="margin-top: 16px"
    >
      <h3 style="margin-top: 0">專案成本明細</h3>
      <el-table :data="projectCost" stripe @row-click="onProjectRowClick">
        <el-table-column label="代碼" prop="code" width="110" />
        <el-table-column label="專案" prop="name" min-width="200" />
        <el-table-column label="預算" width="140">
          <template #default="{ row }"
            >NT$ {{ row.budget.toLocaleString() }}</template
          >
        </el-table-column>
        <el-table-column label="實際工時" prop="hours" width="120">
          <template #default="{ row }">{{ row.hours }} h</template>
        </el-table-column>
        <el-table-column v-if="canSeeCost" label="實際成本" width="160">
          <template #default="{ row }"
            >NT$ {{ (row.cost ?? 0).toLocaleString() }}</template
          >
        </el-table-column>
        <el-table-column v-if="canSeeCost" label="剩餘" width="160">
          <template #default="{ row }">
            <span
              :style="{ color: (row.remaining ?? 0) < 0 ? '#F56C6C' : '#67C23A' }"
            >
              NT$ {{ (row.remaining ?? 0).toLocaleString() }}
            </span>
          </template>
        </el-table-column>
        <el-table-column v-if="canSeeCost" label="使用率" width="160">
          <template #default="{ row }">
            <el-progress
              v-if="row.utilization !== null && row.utilization !== undefined"
              :percentage="Math.min(row.utilization, 100)"
              :status="row.utilization > 100 ? 'exception' : undefined"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default>
            <el-button type="primary" link>明細</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Drill-down dialog -->
    <el-dialog
      v-model="drill.visible"
      width="900px"
      :title="drill.title"
      append-to-body
    >
      <div class="drill-subtitle">
        {{ drill.subtitle }}
        <span class="drill-total">· 共 {{ drill.rows.length }} 筆，合計 {{ drillTotalHours }} h</span>
      </div>
      <el-table
        v-loading="drill.loading"
        :data="drill.rows"
        stripe
        max-height="480"
      >
        <el-table-column label="開始" width="145">
          <template #default="{ row }">{{ fmtTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="結束" width="145">
          <template #default="{ row }">{{ fmtTime(row.end_time) }}</template>
        </el-table-column>
        <el-table-column label="工時" width="80">
          <template #default="{ row }">{{ row.hours }} h</template>
        </el-table-column>
        <el-table-column
          v-if="drill.showUserColumn"
          label="員工"
          prop="user_name"
          width="120"
        />
        <el-table-column label="專案 / 類別" width="180">
          <template #default="{ row }">
            <el-tag
              v-if="row.project_name"
              :style="{ background: row.project_color, color: '#fff', border: 'none' }"
              size="small"
            >
              {{ row.project_name }}
            </el-tag>
            <el-tag
              v-else-if="row.category_name"
              :style="{ background: row.category_color, color: '#fff', border: 'none' }"
              size="small"
            >
              {{ row.category_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="標題 / 描述" min-width="200">
          <template #default="{ row }">
            <div>{{ row.title }}</div>
            <div v-if="row.description" class="desc">{{ row.description }}</div>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  align-items: center;
}
.chart-card {
  padding: 16px;
}
.summary {
  display: flex;
  margin-bottom: 12px;
}
.drill-subtitle {
  color: #606266;
  margin-bottom: 12px;
  font-size: 13px;
}
.drill-total {
  color: #909399;
  margin-left: 6px;
}
.desc {
  color: #909399;
  font-size: 12px;
  margin-top: 2px;
}
</style>
