import axios from "axios";
import { ElMessage } from "element-plus";

const ACCESS_KEY = "token";
const REFRESH_KEY = "refresh_token";

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY) || "",
  getRefresh: () => localStorage.getItem(REFRESH_KEY) || "",
  setAccess: (v) => {
    if (v) localStorage.setItem(ACCESS_KEY, v);
    else localStorage.removeItem(ACCESS_KEY);
  },
  setRefresh: (v) => {
    if (v) localStorage.setItem(REFRESH_KEY, v);
    else localStorage.removeItem(REFRESH_KEY);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

const client = axios.create({
  baseURL: "/api",
  timeout: 15000,
});

client.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// -------- refresh token logic --------
let refreshPromise = null;

async function performRefresh() {
  const refreshToken = tokenStore.getRefresh();
  if (!refreshToken) throw new Error("no refresh token");
  // 用乾淨 axios 避免被本 interceptor 遞迴處理
  const resp = await axios.post(
    "/api/auth/refresh",
    {},
    {
      headers: { Authorization: `Bearer ${refreshToken}` },
      timeout: 15000,
    }
  );
  const newAccess = resp.data.access_token;
  tokenStore.setAccess(newAccess);
  return newAccess;
}

function forceLogout() {
  tokenStore.clear();
  if (!location.pathname.startsWith("/login")) {
    location.replace("/login");
  }
}

client.interceptors.response.use(
  (resp) => resp,
  async (err) => {
    const status = err.response?.status;
    const msg = err.response?.data?.error || err.message || "unknown error";
    const original = err.config || {};

    const isAuthCall =
      typeof original.url === "string" &&
      (original.url.includes("/auth/login") ||
        original.url.includes("/auth/refresh"));

    if (status === 401 && !isAuthCall && !original.__retried) {
      // 嘗試 refresh access token，然後重放
      try {
        if (!refreshPromise) {
          refreshPromise = performRefresh().finally(() => {
            refreshPromise = null;
          });
        }
        const newAccess = await refreshPromise;
        original.__retried = true;
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${newAccess}`;
        return client(original);
      } catch (_) {
        forceLogout();
        return Promise.reject(err);
      }
    }

    if (status === 401) {
      forceLogout();
    } else if (status === 429) {
      ElMessage.error(msg || "請求過於頻繁，請稍候再試");
    } else if (status && status >= 400) {
      ElMessage.error(msg);
    }
    return Promise.reject(err);
  }
);

export default client;
