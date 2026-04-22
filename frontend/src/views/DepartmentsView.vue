<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { departmentsApi, usersApi } from "../api";

const list = ref([]);
const users = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editing = ref(null);

const form = reactive({ name: "", manager_id: null });

async function load() {
  loading.value = true;
  try {
    list.value = await departmentsApi.list();
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  users.value = await usersApi.list();
  await load();
});

function openCreate() {
  editing.value = null;
  form.name = "";
  form.manager_id = null;
  dialogVisible.value = true;
}

function openEdit(row) {
  editing.value = row;
  form.name = row.name;
  form.manager_id = row.manager_id || null;
  dialogVisible.value = true;
}

async function save() {
  try {
    if (editing.value) {
      await departmentsApi.update(editing.value.id, { ...form });
      ElMessage.success("已更新");
    } else {
      if (!form.name) {
        ElMessage.warning("部門名稱必填");
        return;
      }
      await departmentsApi.create({ ...form });
      ElMessage.success("已建立");
    }
    dialogVisible.value = false;
    await load();
  } catch (_) {}
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`確定要刪除部門「${row.name}」嗎？`, "刪除", {
      type: "warning",
    });
  } catch (_) {
    return;
  }
  await departmentsApi.remove(row.id);
  ElMessage.success("已刪除");
  await load();
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>部門管理</h2>
      <el-button type="primary" @click="openCreate">+ 新增部門</el-button>
    </div>
    <div class="card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="ID" prop="id" width="80" />
        <el-table-column label="名稱" prop="name" />
        <el-table-column label="主管" prop="manager_name" width="160" />
        <el-table-column label="成員數" prop="member_count" width="100" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">編輯</el-button>
            <el-button size="small" type="danger" plain @click="remove(row)">
              刪除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '編輯部門' : '新增部門'"
      width="420px"
    >
      <el-form label-width="70px">
        <el-form-item label="名稱">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="主管">
          <el-select
            v-model="form.manager_id"
            clearable
            filterable
            placeholder="選擇主管"
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
