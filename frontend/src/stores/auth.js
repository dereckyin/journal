import { defineStore } from "pinia";
import { authApi } from "../api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("token") || "",
    user: null,
  }),
  getters: {
    isAuthenticated: (s) => !!s.token && !!s.user,
    role: (s) => s.user?.role || null,
    isAdmin: (s) => s.user?.role === "admin",
    isManager: (s) => s.user?.role === "manager",
    isEmployee: (s) => s.user?.role === "employee",
  },
  actions: {
    async login(username, password) {
      const data = await authApi.login(username, password);
      this.token = data.access_token;
      this.user = data.user;
      localStorage.setItem("token", data.access_token);
      return data;
    },
    async fetchMe() {
      const data = await authApi.me();
      this.user = data.user;
      return data.user;
    },
    async logout() {
      try {
        await authApi.logout();
      } catch (_) {
        // ignore
      }
      this.token = "";
      this.user = null;
      localStorage.removeItem("token");
    },
  },
});
