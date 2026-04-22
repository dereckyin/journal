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

import { departmentsApi, reportsApi, usersApi } from "../api";
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

const projectCostOption = computed(() => {
  const rows = projectCost.value || [];
  return {
    title: { text: "專案成本 vs 預算", left: "center" },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { bottom: 0 },
    grid: { top: 60, left: 50, right: 30, bottom: 50 },
    xAxis: {
      type: "category",
      data: rows.map((r) => r.code),
      axisLabel: { interval: 0, rotate: 30 },
    },
    yAxis: { type: "value", axisLabel: { formatter: "{value}" } },
    series: [
      {
        name: "預算",
        type: "bar",
        data: rows.map((r) => r.budget),
        itemStyle: { color: "#91cc75" },
      },
      {
        name: "實際成本",
        type: "bar",
        data: rows.map((r) => r.cost),
        itemStyle: { color: "#ee6666" },
      },
    ],
  };
});

const userHoursPieOption = computed(() => {
  if (!userHours.value) return {};
  const data = [
    ...userHours.value.projects.map((p) => ({
      name: p.name,
      value: p.hours,
      itemStyle: { color: p.color },
    })),
    ...userHours.value.categories.map((c) => ({
      name: c.name,
      value: c.hours,
      itemStyle: { color: c.color },
    })),
  ];
  return {
    title: { text: "個人工時分布", left: "center" },
    tooltip: { trigger: "item", formatter: "{b}: {c} 小時 ({d}%)" },
    legend: { bottom: 0, type: "scroll" },
    series: [
      {
        type: "pie",
        radius: ["40%", "65%"],
        center: ["50%", "48%"],
        data,
        label: { formatter: "{b}\n{c}h" },
      },
    ],
  };
});

const deptBarOption = computed(() => {
  if (!deptSummary.value) return {};
  const rows = deptSummary.value.rows || [];
  return {
    title: { text: "部門成員月工時 / 人力成本", left: "center" },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { bottom: 0 },
    grid: { top: 60, left: 60, right: 60, bottom: 60 },
    xAxis: { type: "category", data: rows.map((r) => r.full_name) },
    yAxis: [
      { type: "value", name: "工時", axisLabel: { formatter: "{value} h" } },
      { type: "value", name: "成本", axisLabel: { formatter: "{value}" } },
    ],
    series: [
      {
        name: "工時",
        type: "bar",
        data: rows.map((r) => r.hours),
        itemStyle: { color: "#5470c6" },
      },
      {
        name: "成本",
        type: "bar",
        yAxisIndex: 1,
        data: rows.map((r) => r.cost),
        itemStyle: { color: "#fac858" },
      },
    ],
  };
});

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
            <el-statistic title="月總工時"
              :value="userHours.total_hours"
              suffix="h"
            />
            <el-statistic
              title="月人力成本"
              :value="userHours.total_cost"
              :precision="0"
              suffix="元"
              style="margin-left: 24px"
            />
          </div>
          <v-chart :option="userHoursPieOption" style="height: 380px" autoresize />
        </div>
      </el-col>
      <el-col v-if="canSeeProjectCost" :span="12">
        <div class="card chart-card">
          <v-chart :option="projectCostOption" style="height: 420px" autoresize />
        </div>
      </el-col>
    </el-row>

    <div v-if="canSeeDeptSummary && deptSummary" class="card chart-card" style="margin-top: 16px">
      <div class="summary">
        <el-statistic
          title="部門總工時"
          :value="deptSummary.total_hours"
          suffix="h"
        />
        <el-statistic
          title="部門總成本"
          :value="deptSummary.total_cost"
          :precision="0"
          suffix="元"
          style="margin-left: 24px"
        />
      </div>
      <v-chart :option="deptBarOption" style="height: 380px" autoresize />

      <el-table :data="deptSummary.rows" stripe style="margin-top: 12px">
        <el-table-column label="員工" prop="full_name" />
        <el-table-column label="部門" prop="department_name" />
        <el-table-column label="工時" prop="hours" width="120">
          <template #default="{ row }">{{ row.hours }} h</template>
        </el-table-column>
        <el-table-column label="人力成本" prop="cost" width="160">
          <template #default="{ row }"
            >NT$ {{ row.cost.toLocaleString() }}</template
          >
        </el-table-column>
      </el-table>
    </div>

    <div
      v-if="canSeeProjectCost && projectCost.length"
      class="card chart-card"
      style="margin-top: 16px"
    >
      <h3 style="margin-top: 0">專案成本明細</h3>
      <el-table :data="projectCost" stripe>
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
        <el-table-column label="實際成本" width="160">
          <template #default="{ row }"
            >NT$ {{ row.cost.toLocaleString() }}</template
          >
        </el-table-column>
        <el-table-column label="剩餘" width="160">
          <template #default="{ row }">
            <span :style="{ color: row.remaining < 0 ? '#F56C6C' : '#67C23A' }">
              NT$ {{ row.remaining.toLocaleString() }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="使用率" width="160">
          <template #default="{ row }">
            <el-progress
              v-if="row.utilization !== null"
              :percentage="Math.min(row.utilization, 100)"
              :status="row.utilization > 100 ? 'exception' : undefined"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
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
</style>
