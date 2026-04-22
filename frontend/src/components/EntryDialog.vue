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

function toLocalIso(v) {
  if (!v) return "";
  const d = v instanceof Date ? v : new Date(v);
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
    } else {
      form.id = null;
      form.title = "";
      form.description = "";
      form.kind = "project";
      form.project_id = props.projects[0]?.id || null;
      form.category_id = null;
      form.start_time = props.defaultStart ? new Date(props.defaultStart) : null;
      form.end_time = props.defaultEnd ? new Date(props.defaultEnd) : null;
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

  const payload = {
    title: form.title.trim(),
    description: form.description,
    start_time: toLocalIso(form.start_time),
    end_time: toLocalIso(form.end_time),
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
        <el-input v-model="form.title" placeholder="例：首頁切版" />
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
