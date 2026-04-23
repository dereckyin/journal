<script setup>
import { onMounted, ref, shallowRef } from "vue";
import FullCalendar from "@fullcalendar/vue3";
import timeGridPlugin from "@fullcalendar/timegrid";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import { ElMessage } from "element-plus";

import {
  categoriesApi,
  entriesApi,
  projectsApi,
  titlePresetsApi,
} from "../api";
import EntryDialog from "../components/EntryDialog.vue";

const calendarRef = ref(null);
const projects = ref([]);
const categories = ref([]);
const titlePresets = ref([]);
const dialogVisible = ref(false);
const currentEntry = ref(null);
const defaultStart = ref(null);
const defaultEnd = ref(null);

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
  selectable: true,
  selectMirror: true,
  editable: true,
  eventResizableFromStart: true,
  height: "auto",
  headerToolbar: {
    left: "prev,next today",
    center: "title",
    right: "timeGridWeek,timeGridDay,dayGridMonth",
  },
  buttonText: {
    today: "今天",
    week: "週",
    day: "日",
    month: "月",
  },
  events: fetchEvents,
  select: onSelect,
  eventClick: onEventClick,
  eventDrop: onEventChange,
  eventResize: onEventChange,
  eventDidMount(info) {
    info.el.setAttribute("title", buildTooltip(info.event.extendedProps));
  },
});

async function fetchEvents(info, success, failure) {
  try {
    const entries = await entriesApi.list({
      from: info.startStr,
      to: info.endStr,
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

function onSelect(info) {
  currentEntry.value = null;
  defaultStart.value = info.start;
  defaultEnd.value = info.end;
  dialogVisible.value = true;
  calendarRef.value?.getApi().unselect();
}

function onEventClick(info) {
  currentEntry.value = info.event.extendedProps;
  dialogVisible.value = true;
}

async function onEventChange(info) {
  const entry = info.event.extendedProps;
  try {
    await entriesApi.update(entry.id, {
      start_time: toLocalIso(info.event.start),
      end_time: toLocalIso(info.event.end),
    });
    ElMessage.success("已更新時間");
    reload();
  } catch (_) {
    info.revert();
  }
}

function toLocalIso(d) {
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:00`
  );
}

onMounted(async () => {
  try {
    const [ps, cs, tps] = await Promise.all([
      projectsApi.list(),
      categoriesApi.list(),
      titlePresetsApi.list(),
    ]);
    projects.value = ps.filter((p) => p.status === "active");
    categories.value = cs;
    titlePresets.value = tps;
  } catch (_) {}
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>我的週曆</h2>
      <div>
        <el-button
          type="primary"
          @click="
            () => {
              currentEntry = null;
              defaultStart = new Date();
              defaultEnd = new Date(Date.now() + 60 * 60 * 1000);
              dialogVisible = true;
            }
          "
        >
          + 新增工作
        </el-button>
      </div>
    </div>
    <div class="card" style="padding: 8px">
      <FullCalendar ref="calendarRef" :options="options" />
    </div>

    <EntryDialog
      v-model="dialogVisible"
      :entry="currentEntry"
      :projects="projects"
      :categories="categories"
      :title-presets="titlePresets"
      :default-start="defaultStart"
      :default-end="defaultEnd"
      @saved="reload"
      @deleted="reload"
    />
  </div>
</template>
