<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { categoriesApi } from "../api";

const list = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editing = ref(null);
const form = reactive({ name: "", color: "#909399" });

async function load() {
  loading.value = true;
  try {
    list.value = await categoriesApi.list();
  } finally {
    loading.value = false;
  }
}

onMounted(load);

function openCreate() {
  editing.value = null;
  form.name = "";
  form.color = "#909399";
  dialogVisible.value = true;
}

function openEdit(row) {
  editing.value = row;
  form.name = row.name;
  form.color = row.color;
  dialogVisible.value = true;
}

async function save() {
  try {
    if (editing.value) {
      await categoriesApi.update(editing.value.id, { ...form });
    } else {
      if (!form.name) {
        ElMessage.warning("類別名稱必填");
        return;
      }
      await categoriesApi.create({ ...form });
    }
    ElMessage.success("已儲存");
    dialogVisible.value = false;
    await load();
  } catch (_) {}
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`刪除類別「${row.name}」？`, "刪除", {
      type: "warning",
    });
  } catch (_) {
    return;
  }
  await categoriesApi.remove(row.id);
  await load();
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>個人工作類別</h2>
      <el-button type="primary" @click="openCreate">+ 新增類別</el-button>
    </div>
    <div class="card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="ID" prop="id" width="80" />
        <el-table-column label="名稱" prop="name" />
        <el-table-column label="顏色" width="160">
          <template #default="{ row }">
            <span
              :style="{
                display: 'inline-block',
                width: '16px',
                height: '16px',
                background: row.color,
                borderRadius: '3px',
                verticalAlign: 'middle',
                marginRight: '8px',
              }"
            ></span>
            {{ row.color }}
          </template>
        </el-table-column>
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
      :title="editing ? '編輯類別' : '新增類別'"
      width="360px"
    >
      <el-form label-width="70px">
        <el-form-item label="名稱">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="顏色">
          <el-color-picker v-model="form.color" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">儲存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
