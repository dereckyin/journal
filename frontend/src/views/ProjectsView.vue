<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { projectsApi, usersApi } from "../api";

const list = ref([]);
const users = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editing = ref(null);

const form = reactive({
  id: null,
  code: "",
  name: "",
  description: "",
  budget: 0,
  color: "#409EFF",
  status: "active",
  start_date: null,
  end_date: null,
  member_ids: [],
});

function resetForm(p) {
  form.id = p?.id || null;
  form.code = p?.code || "";
  form.name = p?.name || "";
  form.description = p?.description || "";
  form.budget = p?.budget || 0;
  form.color = p?.color || "#409EFF";
  form.status = p?.status || "active";
  form.start_date = p?.start_date || null;
  form.end_date = p?.end_date || null;
  form.member_ids = p?.member_ids ? [...p.member_ids] : [];
}

async function load() {
  loading.value = true;
  try {
    list.value = await projectsApi.list();
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await load();
  try {
    users.value = await usersApi.list();
  } catch (_) {}
});

function openCreate() {
  editing.value = null;
  resetForm();
  dialogVisible.value = true;
}

function openEdit(row) {
  editing.value = row;
  resetForm(row);
  dialogVisible.value = true;
}

async function save() {
  const payload = { ...form };
  try {
    if (editing.value) {
      await projectsApi.update(editing.value.id, payload);
      ElMessage.success("已更新");
    } else {
      await projectsApi.create(payload);
      ElMessage.success("已建立");
    }
    dialogVisible.value = false;
    await load();
  } catch (_) {}
}

async function closeProject(row) {
  try {
    await ElMessageBox.confirm(`確定要關閉專案「${row.name}」嗎？`, "關閉專案", {
      type: "warning",
    });
  } catch (_) {
    return;
  }
  await projectsApi.remove(row.id);
  ElMessage.success("已關閉");
  await load();
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>專案管理</h2>
      <el-button type="primary" @click="openCreate">+ 新增專案</el-button>
    </div>
    <div class="card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="代碼" prop="code" width="110" />
        <el-table-column label="名稱" prop="name" min-width="200">
          <template #default="{ row }">
            <span
              class="color-dot"
              :style="{ background: row.color }"
            ></span>
            {{ row.name }}
          </template>
        </el-table-column>
        <el-table-column label="預算" width="140">
          <template #default="{ row }"
            >NT$ {{ row.budget.toLocaleString() }}</template
          >
        </el-table-column>
        <el-table-column label="成員" width="90">
          <template #default="{ row }">{{ row.member_ids.length }} 人</template>
        </el-table-column>
        <el-table-column label="狀態" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'active' ? 'success' : 'info'"
              size="small"
            >
              {{ row.status === "active" ? "進行中" : "已關閉" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="期程" width="220">
          <template #default="{ row }">
            {{ row.start_date || "-" }} ~ {{ row.end_date || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">編輯</el-button>
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="row.status !== 'active'"
              @click="closeProject(row)"
            >
              關閉
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '編輯專案' : '新增專案'"
      width="640px"
    >
      <el-form label-width="80px">
        <el-row :gutter="12">
          <el-col :span="10">
            <el-form-item label="代碼">
              <el-input v-model="form.code" placeholder="PA-001" />
            </el-form-item>
          </el-col>
          <el-col :span="14">
            <el-form-item label="名稱">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="說明">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="10">
            <el-form-item label="預算">
              <el-input-number
                v-model="form.budget"
                :min="0"
                :step="10000"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="顏色">
              <el-color-picker v-model="form.color" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="狀態">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="進行中" value="active" />
                <el-option label="已關閉" value="closed" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="開始">
              <el-date-picker
                v-model="form.start_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="結束">
              <el-date-picker
                v-model="form.end_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="成員">
          <el-select
            v-model="form.member_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="選擇可記錄此專案的員工"
            style="width: 100%"
          >
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="`${u.full_name} (${u.username})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">儲存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.color-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
</style>
