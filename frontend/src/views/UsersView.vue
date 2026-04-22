<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { departmentsApi, usersApi } from "../api";

const list = ref([]);
const departments = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editing = ref(null);

const form = reactive({
  username: "",
  password: "",
  full_name: "",
  email: "",
  role: "employee",
  department_id: null,
  hourly_rate: 0,
  is_active: true,
});

function resetForm(u) {
  form.username = u?.username || "";
  form.password = "";
  form.full_name = u?.full_name || "";
  form.email = u?.email || "";
  form.role = u?.role || "employee";
  form.department_id = u?.department_id || null;
  form.hourly_rate = u?.hourly_rate || 0;
  form.is_active = u?.is_active ?? true;
}

async function load() {
  loading.value = true;
  try {
    list.value = await usersApi.list();
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  departments.value = await departmentsApi.list();
  await load();
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
  try {
    if (editing.value) {
      const payload = { ...form };
      if (!payload.password) delete payload.password;
      await usersApi.update(editing.value.id, payload);
      ElMessage.success("已更新");
    } else {
      if (!form.username || !form.password || !form.full_name) {
        ElMessage.warning("帳號、密碼、姓名必填");
        return;
      }
      await usersApi.create({ ...form });
      ElMessage.success("已建立");
    }
    dialogVisible.value = false;
    await load();
  } catch (_) {}
}

async function disableUser(row) {
  try {
    await ElMessageBox.confirm(
      `確定要停用員工「${row.full_name}」嗎？`,
      "停用確認",
      { type: "warning" }
    );
  } catch (_) {
    return;
  }
  await usersApi.remove(row.id);
  ElMessage.success("已停用");
  await load();
}

const roleLabel = {
  admin: "管理者",
  manager: "主管",
  employee: "員工",
};
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>員工管理</h2>
      <el-button type="primary" @click="openCreate">+ 新增員工</el-button>
    </div>
    <div class="card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="帳號" prop="username" width="120" />
        <el-table-column label="姓名" prop="full_name" width="140" />
        <el-table-column label="Email" prop="email" min-width="180" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag
              :type="
                row.role === 'admin'
                  ? 'danger'
                  : row.role === 'manager'
                  ? 'warning'
                  : 'info'
              "
              size="small"
            >
              {{ roleLabel[row.role] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="部門"
          prop="department_name"
          width="120"
        />
        <el-table-column label="時薪" width="120">
          <template #default="{ row }"
            >NT$ {{ (row.hourly_rate || 0).toLocaleString() }}</template
          >
        </el-table-column>
        <el-table-column label="狀態" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{
              row.is_active ? "啟用" : "停用"
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">編輯</el-button>
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="!row.is_active"
              @click="disableUser(row)"
            >
              停用
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '編輯員工' : '新增員工'"
      width="560px"
    >
      <el-form label-width="80px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="帳號">
              <el-input v-model="form.username" :disabled="!!editing" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密碼">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                :placeholder="editing ? '留白表示不變更' : ''"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="姓名">
              <el-input v-model="form.full_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Email">
              <el-input v-model="form.email" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="角色">
              <el-select v-model="form.role" style="width: 100%">
                <el-option label="員工" value="employee" />
                <el-option label="主管" value="manager" />
                <el-option label="管理者" value="admin" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="部門">
              <el-select
                v-model="form.department_id"
                clearable
                style="width: 100%"
              >
                <el-option
                  v-for="d in departments"
                  :key="d.id"
                  :label="d.name"
                  :value="d.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="時薪">
              <el-input-number
                v-model="form.hourly_rate"
                :min="0"
                :step="50"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="啟用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">儲存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
