<script setup>
import { reactive, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const form = reactive({ username: "", password: "" });
const loading = ref(false);

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning("請輸入帳號與密碼");
    return;
  }
  loading.value = true;
  try {
    await auth.login(form.username, form.password);
    ElMessage.success(`歡迎，${auth.user.full_name}`);
    const redirect = route.query.redirect || "/calendar";
    router.push(redirect);
  } catch (_) {
    // interceptor already shows error
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <h1>工作日誌</h1>
      <p class="subtitle">Work Journal</p>
      <el-form :model="form" @keydown.enter="submit">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="帳號"
            size="large"
            :prefix-icon="'User'"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密碼"
            size="large"
            show-password
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          style="width: 100%"
          :loading="loading"
          @click="submit"
        >
          登入
        </el-button>
      </el-form>
      <div class="hint">
        <p>預設帳號：</p>
        <ul>
          <li>admin / admin123（管理者）</li>
          <li>manager1 / manager123（主管）</li>
          <li>emp1 / emp123（員工）</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 380px;
  background: #fff;
  border-radius: 12px;
  padding: 36px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}
.login-card h1 {
  margin: 0;
  font-size: 28px;
  text-align: center;
}
.subtitle {
  text-align: center;
  color: #909399;
  margin: 4px 0 24px;
}
.hint {
  margin-top: 18px;
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 10px 14px;
  border-radius: 6px;
}
.hint ul {
  margin: 4px 0 0;
  padding-left: 18px;
}
.hint p {
  margin: 0;
}
</style>
