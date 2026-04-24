<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  changeRequestsApi,
  projectsApi,
  usersApi,
} from "../api";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

const loading = ref(false);
const rows = ref([]);
const projects = ref([]);
const users = ref([]);

const scope = ref("mine");
const statusFilter = ref("");

const dialogVisible = ref(false);
const editingId = ref(null);
const form = reactive({
  title: "",
  description: "",
  project_id: null,
  approver_id: null,
});

const rejectDialogVisible = ref(false);
const rejectTargetId = ref(null);
const rejectNote = ref("");

const statusLabel = {
  draft: "草稿",
  submitted: "待簽核",
  approved: "已核准",
  rejected: "已駁回",
};

const statusTag = {
  draft: "info",
  submitted: "warning",
  approved: "success",
  rejected: "danger",
};

const canUseDeptScope = computed(
  () => auth.isAdmin || auth.isManager
);
const canUseAllScope = computed(() => auth.isAdmin);

const scopeOptions = computed(() => {
  const opts = [{ label: "我的申請", value: "mine" }];
  opts.push({ label: "待我簽核", value: "pending" });
  if (canUseDeptScope.value) {
    opts.push({ label: "部門申請", value: "department" });
  }
  if (canUseAllScope.value) {
    opts.push({ label: "全部", value: "all" });
  }
  return opts;
});

function canApproveRow(row) {
  if (row.status !== "submitted") return false;
  if (auth.isAdmin) return true;
  return row.effective_approver_id === auth.user?.id;
}

function canEditRow(row) {
  if (row.requester_id !== auth.user?.id && !auth.isAdmin) return false;
  return row.status === "draft" || row.status === "rejected";
}

async function load() {
  loading.value = true;
  try {
    const params = { scope: scope.value };
    if (statusFilter.value) params.status = statusFilter.value;
    rows.value = await changeRequestsApi.list(params);
  } catch (_) {
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

watch([scope, statusFilter], load);

onMounted(async () => {
  try {
    const ps = await projectsApi.list();
    projects.value = ps.filter((p) => p.status === "active");
    if (auth.isAdmin || auth.isManager) {
      const us = await usersApi.list();
      users.value = (us || []).filter((u) => u.is_active);
    } else {
      users.value = [];
    }
  } catch (_) {}
  await load();
});

function openCreate() {
  editingId.value = null;
  form.title = "";
  form.description = "";
  form.project_id = null;
  form.approver_id = null;
  dialogVisible.value = true;
}

function openEdit(row) {
  editingId.value = row.id;
  form.title = row.title;
  form.description = row.description || "";
  form.project_id = row.project_id || null;
  form.approver_id = row.approver_id || null;
  dialogVisible.value = true;
}

async function saveForm() {
  const title = (form.title || "").trim();
  if (!title) {
    ElMessage.warning("請輸入標題");
    return;
  }
  try {
    const payload = {
      title,
      description: form.description || null,
      project_id: form.project_id || null,
      approver_id: form.approver_id || null,
    };
    if (editingId.value) {
      await changeRequestsApi.update(editingId.value, payload);
      ElMessage.success("已更新");
    } else {
      await changeRequestsApi.create(payload);
      ElMessage.success("已建立");
    }
    dialogVisible.value = false;
    await load();
  } catch (_) {}
}

async function submitRow(row) {
  try {
    await ElMessageBox.confirm("送審後將由簽核人核准或駁回，確定嗎？", "送審確認", {
      type: "warning",
    });
  } catch (_) {
    return;
  }
  try {
    await changeRequestsApi.submit(row.id);
    ElMessage.success("已送審");
    await load();
  } catch (_) {}
}

async function approveRow(row) {
  try {
    await ElMessageBox.confirm(`核准「${row.title}」？`, "核准", {
      type: "success",
    });
  } catch (_) {
    return;
  }
  try {
    await changeRequestsApi.approve(row.id, {});
    ElMessage.success("已核准");
    await load();
  } catch (_) {}
}

function openReject(row) {
  rejectTargetId.value = row.id;
  rejectNote.value = "";
  rejectDialogVisible.value = true;
}

async function confirmReject() {
  const note = (rejectNote.value || "").trim();
  if (!note) {
    ElMessage.warning("請填寫駁回原因");
    return;
  }
  try {
    await changeRequestsApi.reject(rejectTargetId.value, {
      decision_note: note,
    });
    ElMessage.success("已駁回");
    rejectDialogVisible.value = false;
    await load();
  } catch (_) {}
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(`刪除草稿「${row.title}」？`, "刪除", {
      type: "warning",
    });
  } catch (_) {
    return;
  }
  try {
    await changeRequestsApi.remove(row.id);
    ElMessage.success("已刪除");
    await load();
  } catch (_) {}
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>需求單（變更申請）</h2>
      <el-button type="primary" @click="openCreate">+ 新增需求單</el-button>
    </div>

    <div class="card" style="padding: 16px">
      <div class="toolbar">
        <el-radio-group v-model="scope" size="small">
          <el-radio-button
            v-for="o in scopeOptions"
            :key="o.value"
            :value="o.value"
          >
            {{ o.label }}
          </el-radio-button>
        </el-radio-group>
        <el-select
          v-model="statusFilter"
          placeholder="狀態篩選"
          clearable
          style="width: 140px; margin-left: 12px"
        >
          <el-option label="全部狀態" value="" />
          <el-option label="草稿" value="draft" />
          <el-option label="待簽核" value="submitted" />
          <el-option label="已核准" value="approved" />
          <el-option label="已駁回" value="rejected" />
        </el-select>
      </div>

      <el-table v-loading="loading" :data="rows" stripe style="margin-top: 12px">
        <el-table-column prop="id" label="#" width="64" />
        <el-table-column prop="title" label="標題" min-width="160" />
        <el-table-column prop="requester_name" label="申請人" width="100" />
        <el-table-column label="專案" min-width="120">
          <template #default="{ row }">
            <span v-if="row.project_code">
              [{{ row.project_code }}] {{ row.project_name }}
            </span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="狀態" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag[row.status] || 'info'" size="small">
              {{ statusLabel[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="submitted_at" label="送審時間" width="170" />
        <el-table-column prop="decided_at" label="簽核時間" width="170" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="canEditRow(row)"
              size="small"
              link
              type="primary"
              @click="openEdit(row)"
            >
              編輯
            </el-button>
            <el-button
              v-if="
                canEditRow(row) &&
                (row.status === 'draft' || row.status === 'rejected') &&
                row.requester_id === auth.user?.id
              "
              size="small"
              link
              type="warning"
              @click="submitRow(row)"
            >
              送審
            </el-button>
            <el-button
              v-if="canApproveRow(row)"
              size="small"
              link
              type="success"
              @click="approveRow(row)"
            >
              核准
            </el-button>
            <el-button
              v-if="canApproveRow(row)"
              size="small"
              link
              type="danger"
              @click="openReject(row)"
            >
              駁回
            </el-button>
            <el-button
              v-if="
                row.status === 'draft' &&
                (row.requester_id === auth.user?.id || auth.isAdmin)
              "
              size="small"
              link
              type="danger"
              @click="deleteRow(row)"
            >
              刪除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="尚無資料" />
        </template>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '編輯需求單' : '新增需求單'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form label-width="88px">
        <el-form-item label="標題" required>
          <el-input v-model="form.title" placeholder="簡要說明需求" />
        </el-form-item>
        <el-form-item label="說明">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="詳細內容"
          />
        </el-form-item>
        <el-form-item label="關聯專案">
          <el-select
            v-model="form.project_id"
            clearable
            filterable
            placeholder="選填"
            style="width: 100%"
          >
            <el-option
              v-for="p in projects"
              :key="p.id"
              :label="`[${p.code}] ${p.name}`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="簽核人">
          <el-select
            v-model="form.approver_id"
            clearable
            filterable
            placeholder="選填（未指定則由部門主管簽核）"
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
        <el-button type="primary" @click="saveForm">儲存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="rejectDialogVisible"
      title="駁回需求單"
      width="440px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="rejectNote"
        type="textarea"
        :rows="4"
        placeholder="請填寫駁回原因（必填）"
      />
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">確認駁回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.muted {
  color: #909399;
}
</style>
