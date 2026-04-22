import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("../views/LoginView.vue"),
    meta: { guest: true },
  },
  {
    path: "/",
    component: () => import("../layouts/MainLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "", redirect: "/calendar" },
      {
        path: "calendar",
        name: "calendar",
        component: () => import("../views/CalendarView.vue"),
      },
      {
        path: "team",
        name: "team",
        component: () => import("../views/TeamCalendarView.vue"),
        meta: { roles: ["manager", "admin"] },
      },
      {
        path: "reports",
        name: "reports",
        component: () => import("../views/ReportsView.vue"),
      },
      {
        path: "admin/projects",
        name: "admin-projects",
        component: () => import("../views/ProjectsView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "admin/users",
        name: "admin-users",
        component: () => import("../views/UsersView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "admin/departments",
        name: "admin-departments",
        component: () => import("../views/DepartmentsView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "admin/categories",
        name: "admin-categories",
        component: () => import("../views/CategoriesView.vue"),
        meta: { roles: ["admin"] },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe();
    } catch (_) {
      auth.token = "";
      localStorage.removeItem("token");
    }
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  if (to.meta.guest && auth.isAuthenticated) {
    return { path: "/calendar" };
  }
  if (to.meta.roles && !to.meta.roles.includes(auth.role)) {
    return { path: "/calendar" };
  }
  return true;
});

export default router;
