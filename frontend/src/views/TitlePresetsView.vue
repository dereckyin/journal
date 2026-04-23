<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { titlePresetsApi } from "../api";

const activeKind = ref("project");
const all = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editing = ref(null);
const form = reactive({ name: "", sort_order: 0 });

const rows = computed(() =>
  all.value
    .filter((r) => r.kind === activeKind.value)
    .slice()
    .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
);

async function load() {
  loading.value = true;
  try {
    all.value = await titlePresetsApi.list();
  } finally {
    loading.value = false;
  }
}

onMounted(load);

function openCreate() {
  editing.value = null;
  form.name = "";
  form.sort_order = rows.value.length
    ? rows.value[rows.value.length - 1].sort_order + 1
    : 0;
  dialogVisible.value = true;
}

function openEdit(row) {
  editing.value = row;
  form.name = row.name;
  form.sort_order = row.sort_order;
  dialogVisible.value = true;
}

async function save() {
  const name = (form.name || "").trim();
  if (!name) {
    ElMessage.warning("名稱必填");
    return;
  }
  try {
    if (editing.value) {
      await titlePresetsApi.update(editing.value.id, {
        name,
        sort_order: Number(form.sort_order) || 0,
      });
    } else {
      await titlePresetsApi.create({
        kind: activeKind.value,
        name,
        sort_order: Number(form.sort_order) || 0,
      });
    }
    ElMessage.success("已儲存");
    dialogVisible.value = false;
    await load();
  } catch (_) {}
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`刪除預設標題「${row.name}」？`, "刪除", {
      type: "warning",
    });
  } catch (_) {
    return;
  }
  try {
    await titlePresetsApi.remove(row.id);
    ElMessage.success("已刪除");
    await load();
  } catch (_) {}
}

async function moveUp(row) {
  const list = rows.value;
  const idx = list.findIndex((r) => r.id === row.id);
  if (idx <= 0) return;
  const prev = list[idx - 1];
  await swapSortOrder(row, prev);
}

async function moveDown(row) {
  const list = rows.value;
  const idx = list.findIndex((r) => r.id === row.id);
  if (idx < 0 || idx >= list.length - 1) return;
  const next = list[idx + 1];
  await swapSortOrder(row, next);
}

async function swapSortOrder(a, b) {
  // 若兩者 sort_order 相同，給 a 用 b+1 / b-1 方式拉開；否則直接交換
  const aOrder = a.sort_order;
  const bOrder = b.sort_order;
  try {
    if (aOrder === bOrder) {
      await titlePresetsApi.update(a.id, { sort_order: bOrder - 1 });
    } else {
      await titlePresetsApi.update(a.id, { sort_order: bOrder });
      await titlePresetsApi.update(b.id, { sort_order: aOrder });
    }
    await load();
  } catch (_) {}
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>標題預設</h2>
      <el-button type="primary" @click="openCreate">+ 新增預設</el-button>
    </div>

    <div class="card">
      <el-tabs v-model="activeKind">
        <el-tab-pane label="專案類型" name="project" />
        <el-tab-pane label="個人類別" name="category" />
      </el-tabs>

      <el-alert
        v-if="activeKind === 'project'"
        type="info"
        :closable="false"
        show-icon
        title="「工作紀錄」選『專案』類型時會顯示這組下拉。員工仍可自行輸入自訂標題。"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-else
        type="info"
        :closable="false"
        show-icon
        title="「工作紀錄」選『個人事項』類型時會顯示這組下拉。員工仍可自行輸入自訂標題。"
        style="margin-bottom: 12px"
      />

      <el-table :data="rows" v-loading="loading" stripe>
        <el-table-column label="排序" width="90">
          <template #default="{ row, $index }">
            <div class="order-cell">
              <span class="order-num">{{ row.sort_order }}</span>
              <div class="order-btns">
                <el-button
                  size="small"
                  link
                  :disabled="$index === 0"
                  @click="moveUp(row)"
                  title="上移"
                  >↑</el-button
                >
                <el-button
                  size="small"
                  link
                  :disabled="$index === rows.length - 1"
                  @click="moveDown(row)"
                  title="下移"
                  >↓</el-button
                >
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="名稱" prop="name" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">編輯</el-button>
            <el-button size="small" type="danger" plain @click="remove(row)">
              刪除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="尚無預設，點右上角『+ 新增預設』" />
        </template>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '編輯預設' : '新增預設'"
      width="380px"
    >
      <el-form label-width="70px">
        <el-form-item label="類型">
          <el-tag>
            {{ activeKind === "project" ? "專案類型" : "個人類別" }}
          </el-tag>
        </el-form-item>
        <el-form-item label="名稱">
          <el-input v-model="form.name" placeholder="例：會議 / 開發 / 測試" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :step="1" />
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
.order-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}
.order-num {
  display: inline-block;
  min-width: 18px;
  color: #606266;
}
.order-btns {
  display: inline-flex;
  flex-direction: column;
  line-height: 1;
}
</style>
