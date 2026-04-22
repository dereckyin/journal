import axios from "axios";
import { ElMessage } from "element-plus";

const client = axios.create({
  baseURL: "/api",
  timeout: 15000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const status = err.response?.status;
    const msg = err.response?.data?.error || err.message || "unknown error";

    if (status === 401) {
      localStorage.removeItem("token");
      if (!location.pathname.startsWith("/login")) {
        location.replace("/login");
      }
    } else if (status && status >= 400) {
      ElMessage.error(msg);
    }
    return Promise.reject(err);
  }
);

export default client;
