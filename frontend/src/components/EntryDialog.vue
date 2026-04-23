<script setup>
import { computed, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { entriesApi } from "../api";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  entry: { type: Object, default: null },
  projects: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  defaultStart: { type: [Date, String, null], default: null },
  defaultEnd: { type: [Date, String, null], default: null },
});
const emit = defineEmits(["update:modelValue", "saved", "deleted"]);

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const form = reactive({
  id: null,
  title: "",
  description: "",
  kind: "project", // "project" | "category"
  project_id: null,
  category_id: null,
  start_time: null,
  end_time: null,
});

const loading = ref(false);

// 記住上一次「自動產生」的標題內容；只有當使用者沒改過（或還是空的）時，
// 才會隨著類型 / 專案 / 類別變更自動覆寫，避免蓋掉使用者打字的內容。
const lastAutoTitle = ref("");

const suggestedTitle = computed(() => {
  if (form.kind === "project") {
    const p = props.projects.find((x) => x.id === form.project_id);
    return p ? p.name : "";
  }
  const c = props.categories.find((x) => x.id === form.category_id);
  return c ? c.name : "";
});

function applySuggestion(force = false) {
  const next = suggestedTitle.value;
  if (!next) return;
  const current = (form.title || "").trim();
  if (force || !current || current === lastAutoTitle.value) {
    form.title = next;
    lastAutoTitle.value = next;
  }
}

// 類型切換 / 專案 or 類別切換 → 嘗試自動帶入標題
watch(
  () => [form.kind, form.project_id, form.category_id],
  () => {
    applySuggestion(false);
  }
);

function toLocalIso(v) {
  if (v === null || v === undefined || v === "") return "";
  let d;
  if (v instanceof Date) d = v;
  else if (typeof v === "number") d = new Date(v);
  else if (typeof v === "string") {
    // el-date-picker + value-format="x" 會把 v-model 寫成「數字字串」(毫秒)
    // 直接 new Date("1714020000000") 會回 Invalid Date，需先轉 Number
    const num = Number(v);
    d = Number.isFinite(num) && /^\d+$/.test(v) ? new Date(num) : new Date(v);
  } else d = new Date(v);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:00`
  );
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    if (props.entry) {
      form.id = props.entry.id;
      form.title = props.entry.title;
      form.description = props.entry.description || "";
      form.start_time = new Date(props.entry.start_time);
      form.end_time = new Date(props.entry.end_time);
      if (props.entry.project_id) {
        form.kind = "project";
        form.project_id = props.entry.project_id;
        form.category_id = null;
      } else {
        form.kind = "category";
        form.category_id = props.entry.category_id;
        form.project_id = null;
      }
      // 編輯時不自動蓋標題；但若標題恰好與目前選項同名，仍允許之後隨選單自動更新
      lastAutoTitle.value = form.title || "";
    } else {
      form.id = null;
      form.title = "";
      form.description = "";
      form.kind = "project";
      form.project_id = props.projects[0]?.id || null;
      form.category_id = null;
      form.start_time = props.defaultStart ? new Date(props.defaultStart) : null;
      form.end_time = props.defaultEnd ? new Date(props.defaultEnd) : null;
      lastAutoTitle.value = "";
      // 讓初始選中的專案立刻帶入標題建議
      applySuggestion(false);
    }
  }
);

const isEdit = computed(() => !!form.id);

async function save() {
  if (!form.title.trim()) {
    ElMessage.warning("請輸入標題");
    return;
  }
  if (!form.start_time || !form.end_time) {
    ElMessage.warning("請選擇起訖時間");
    return;
  }
  if (form.kind === "project" && !form.project_id) {
    ElMessage.warning("請選擇專案");
    return;
  }
  if (form.kind === "category" && !form.category_id) {
    ElMessage.warning("請選擇個人類別");
    return;
  }

  const startIso = toLocalIso(form.start_time);
  const endIso = toLocalIso(form.end_time);
  if (!startIso || !endIso) {
    ElMessage.warning("請選擇有效的起訖時間");
    return;
  }

  const payload = {
    title: form.title.trim(),
    description: form.description,
    start_time: startIso,
    end_time: endIso,
    project_id: form.kind === "project" ? form.project_id : null,
    category_id: form.kind === "category" ? form.category_id : null,
  };

  loading.value = true;
  try {
    if (isEdit.value) {
      const updated = await entriesApi.update(form.id, payload);
      ElMessage.success("已更新");
      emit("saved", updated);
    } else {
      const created = await entriesApi.create(payload);
      ElMessage.success("已建立");
      emit("saved", created);
    }
    visible.value = false;
  } catch (_) {
    // interceptor handles toast
  } finally {
    loading.value = false;
  }
}

async function remove() {
  if (!isEdit.value) return;
  try {
    await ElMessageBox.confirm("確定要刪除這筆工作記錄嗎？", "刪除確認", {
      type: "warning",
    });
  } catch (_) {
    return;
  }
  loading.value = true;
  try {
    await entriesApi.remove(form.id);
    ElMessage.success("已刪除");
    emit("deleted", form.id);
    visible.value = false;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '編輯工作記錄' : '新增工作記錄'"
    width="520px"
    :close-on-click-modal="false"
  >
    <el-form label-width="80px">
      <el-form-item label="類型">
        <el-radio-group v-model="form.kind">
          <el-radio-button value="project">專案</el-radio-button>
          <el-radio-button value="category">個人事項</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.kind === 'project'" label="專案">
        <el-select
          v-model="form.project_id"
          placeholder="選擇專案"
          style="width: 100%"
          filterable
        >
          <el-option
            v-for="p in projects"
            :key="p.id"
            :label="`[${p.code}] ${p.name}`"
            :value="p.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item v-else label="個人類別">
        <el-select
          v-model="form.category_id"
          placeholder="選擇類別"
          style="width: 100%"
        >
          <el-option
            v-for="c in categories"
            :key="c.id"
            :label="c.name"
            :value="c.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="標題">
        <el-input
          v-model="form.title"
          :placeholder="suggestedTitle || '例：首頁切版'"
        >
          <template v-if="suggestedTitle && form.title !== suggestedTitle" #append>
            <el-button @click="applySuggestion(true)" title="套用建議標題">
              套用「{{ suggestedTitle }}」
            </el-button>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item label="起始">
        <el-date-picker
          v-model="form.start_time"
          type="datetime"
          format="YYYY-MM-DD HH:mm"
          value-format="x"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="結束">
        <el-date-picker
          v-model="form.end_time"
          type="datetime"
          format="YYYY-MM-DD HH:mm"
          value-format="x"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="備註">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="工作內容細節"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button v-if="isEdit" type="danger" :loading="loading" @click="remove">
        刪除
      </el-button>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="save">儲存</el-button>
    </template>
  </el-dialog>
</template>
