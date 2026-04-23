<script setup>
import { computed, onMounted, ref, shallowRef } from "vue";
import FullCalendar from "@fullcalendar/vue3";
import timeGridPlugin from "@fullcalendar/timegrid";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";

import { entriesApi, usersApi } from "../api";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const calendarRef = ref(null);
const users = ref([]);
const selectedUserId = ref(null);

const pageTitle = computed(() => (auth.isAdmin ? "全員週曆" : "部門週曆"));

const selectedUserLabel = computed(() => {
  const u = users.value.find((x) => x.id === selectedUserId.value);
  return u ? `${u.full_name} (${u.username})` : "";
});

function fmtRange(start, end) {
  const pad = (n) => String(n).padStart(2, "0");
  const d = (x) =>
    `${x.getFullYear()}/${pad(x.getMonth() + 1)}/${pad(x.getDate())}`;
  const t = (x) => `${pad(x.getHours())}:${pad(x.getMinutes())}`;
  if (!start) return "";
  const s = new Date(start);
  const e = end ? new Date(end) : null;
  if (!e) return `${d(s)} ${t(s)}`;
  if (d(s) === d(e)) return `${d(s)} ${t(s)} - ${t(e)}`;
  return `${d(s)} ${t(s)} - ${d(e)} ${t(e)}`;
}

function buildTooltip(e) {
  const lines = [];
  lines.push(`👤 ${e.user_name || "-"}`);
  lines.push(`📌 ${e.title || ""}`);
  if (e.project_name) lines.push(`📂 專案：${e.project_name}`);
  else if (e.category_name) lines.push(`🏷 類別：${e.category_name}`);
  lines.push(`🕒 ${fmtRange(e.start_time, e.end_time)}（${e.hours ?? 0} h）`);
  if (e.description) lines.push(`📝 ${e.description}`);
  return lines.join("\n");
}

const options = shallowRef({
  plugins: [timeGridPlugin, dayGridPlugin, interactionPlugin],
  initialView: "timeGridWeek",
  locale: "zh-tw",
  firstDay: 1,
  slotMinTime: "07:00:00",
  slotMaxTime: "22:00:00",
  allDaySlot: false,
  nowIndicator: true,
  selectable: false,
  editable: false,
  height: "auto",
  headerToolbar: {
    left: "prev,next today",
    center: "title",
    right: "timeGridWeek,timeGridDay,dayGridMonth",
  },
  buttonText: { today: "今天", week: "週", day: "日", month: "月" },
  events: fetchEvents,
  eventDidMount(info) {
    const e = info.event.extendedProps;
    info.el.setAttribute("title", buildTooltip(e));
  },
});

async function fetchEvents(info, success, failure) {
  if (!selectedUserId.value) {
    success([]);
    return;
  }
  try {
    const entries = await entriesApi.list({
      from: info.startStr,
      to: info.endStr,
      user_id: selectedUserId.value,
    });
    success(
      entries.map((e) => ({
        id: String(e.id),
        title: e.title,
        start: e.start_time,
        end: e.end_time,
        backgroundColor: e.project_color || e.category_color || "#909399",
        borderColor: e.project_color || e.category_color || "#909399",
        extendedProps: e,
      }))
    );
  } catch (err) {
    failure(err);
  }
}

function reload() {
  calendarRef.value?.getApi().refetchEvents();
}

onMounted(async () => {
  try {
    const all = await usersApi.list();
    users.value = all.filter(
      (u) =>
        u.is_active &&
        (auth.isAdmin ||
          (auth.isManager && u.department_id === auth.user?.department_id))
    );
    // 預設挑第一個非本人的成員；若沒有則 fallback 為自己
    const me = auth.user?.id;
    const firstOther = users.value.find((u) => u.id !== me);
    selectedUserId.value = firstOther?.id || me || users.value[0]?.id || null;
    reload();
  } catch (_) {}
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>
        {{ pageTitle }}
        <span v-if="selectedUserLabel" class="viewing-label"
          >· 正在檢視：{{ selectedUserLabel }}</span
        >
      </h2>
      <el-select
        v-model="selectedUserId"
        placeholder="選擇要檢視的成員"
        filterable
        style="width: 240px"
        @change="reload"
      >
        <el-option
          v-for="u in users"
          :key="u.id"
          :label="`${u.full_name} (${u.username})`"
          :value="u.id"
        />
      </el-select>
    </div>
    <div class="card" style="padding: 8px">
      <el-empty
        v-if="!selectedUserId"
        description="請先選擇要檢視的成員"
        :image-size="80"
      />
      <FullCalendar v-else ref="calendarRef" :options="options" />
    </div>
  </div>
</template>

<style scoped>
.viewing-label {
  margin-left: 10px;
  font-size: 14px;
  font-weight: normal;
  color: #909399;
}
</style>
