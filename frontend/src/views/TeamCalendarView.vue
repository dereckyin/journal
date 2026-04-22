<script setup>
import { onMounted, ref, shallowRef } from "vue";
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
});

async function fetchEvents(info, success, failure) {
  try {
    const params = { from: info.startStr, to: info.endStr };
    if (selectedUserId.value) {
      params.user_id = selectedUserId.value;
    } else {
      params.scope = "team";
    }
    const entries = await entriesApi.list(params);
    success(
      entries.map((e) => ({
        id: String(e.id),
        title: `[${e.user_name}] ${e.title}`,
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
  } catch (_) {}
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>部門週曆</h2>
      <el-select
        v-model="selectedUserId"
        placeholder="全部成員"
        clearable
        style="width: 220px"
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
      <FullCalendar ref="calendarRef" :options="options" />
    </div>
  </div>
</template>
