import client, { tokenStore } from "./client";

export { tokenStore };

export const authApi = {
  login: (username, password) =>
    client.post("/auth/login", { username, password }).then((r) => r.data),
  me: () => client.get("/auth/me").then((r) => r.data),
  logout: () => client.post("/auth/logout").then((r) => r.data),
  refresh: () => client.post("/auth/refresh").then((r) => r.data),
};

export const usersApi = {
  list: () => client.get("/users").then((r) => r.data),
  create: (payload) => client.post("/users", payload).then((r) => r.data),
  update: (id, payload) =>
    client.patch(`/users/${id}`, payload).then((r) => r.data),
  remove: (id) => client.delete(`/users/${id}`).then((r) => r.data),
};

export const departmentsApi = {
  list: () => client.get("/departments").then((r) => r.data),
  create: (payload) =>
    client.post("/departments", payload).then((r) => r.data),
  update: (id, payload) =>
    client.patch(`/departments/${id}`, payload).then((r) => r.data),
  remove: (id) => client.delete(`/departments/${id}`).then((r) => r.data),
};

export const projectsApi = {
  list: (mine = false) =>
    client
      .get("/projects", { params: mine ? { mine: 1 } : {} })
      .then((r) => r.data),
  create: (payload) => client.post("/projects", payload).then((r) => r.data),
  update: (id, payload) =>
    client.patch(`/projects/${id}`, payload).then((r) => r.data),
  remove: (id) => client.delete(`/projects/${id}`).then((r) => r.data),
};

export const categoriesApi = {
  list: () => client.get("/categories").then((r) => r.data),
  create: (payload) =>
    client.post("/categories", payload).then((r) => r.data),
  update: (id, payload) =>
    client.patch(`/categories/${id}`, payload).then((r) => r.data),
  remove: (id) => client.delete(`/categories/${id}`).then((r) => r.data),
};

export const entriesApi = {
  list: (params) => client.get("/entries", { params }).then((r) => r.data),
  create: (payload) => client.post("/entries", payload).then((r) => r.data),
  update: (id, payload) =>
    client.patch(`/entries/${id}`, payload).then((r) => r.data),
  remove: (id) => client.delete(`/entries/${id}`).then((r) => r.data),
};

export const reportsApi = {
  projectCost: (projectId) =>
    client
      .get("/reports/project-cost", {
        params: projectId ? { project_id: projectId } : {},
      })
      .then((r) => r.data),
  userHours: (params) =>
    client.get("/reports/user-hours", { params }).then((r) => r.data),
  departmentSummary: (params) =>
    client.get("/reports/department-summary", { params }).then((r) => r.data),
};

export const auditApi = {
  list: (params) =>
    client.get("/audit-logs", { params }).then((r) => r.data),
};

export const titlePresetsApi = {
  list: (kind) =>
    client
      .get("/title-presets", { params: kind ? { kind } : {} })
      .then((r) => r.data),
  create: (payload) =>
    client.post("/title-presets", payload).then((r) => r.data),
  update: (id, payload) =>
    client.patch(`/title-presets/${id}`, payload).then((r) => r.data),
  remove: (id) => client.delete(`/title-presets/${id}`).then((r) => r.data),
};
