import { defineStore } from "pinia";
import { authApi, tokenStore } from "../api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: tokenStore.getAccess(),
    refreshToken: tokenStore.getRefresh(),
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
      this.refreshToken = data.refresh_token || "";
      this.user = data.user;
      tokenStore.setAccess(data.access_token);
      tokenStore.setRefresh(data.refresh_token || "");
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
      this.refreshToken = "";
      this.user = null;
      tokenStore.clear();
    },
  },
});
