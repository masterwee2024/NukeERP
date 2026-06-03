import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { AuthProvider } from "./contexts/AuthContext";
import { ConfirmProvider } from "./components/ui/ConfirmDialog";
import AppLayout from "./components/Layout/AppLayout";
import ProtectedRoute from "./components/Auth/ProtectedRoute";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

// Listen for concurrency conflicts — invalidate data and notify user
if (typeof window !== "undefined") {
  window.addEventListener("concurrency-conflict", ((event: CustomEvent) => {
    const { message } = event.detail;
    queryClient.invalidateQueries();
    console.warn("Concurrency conflict:", message);
  }) as EventListener);
}

const LoginPage = lazy(() => import("./pages/Login"));
const RegisterPage = lazy(() => import("./pages/Register"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPassword"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPassword"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const UserListPage = lazy(() => import("./pages/admin/UserListPage"));
const UserFormPage = lazy(() => import("./pages/admin/UserFormPage"));
const PageList = lazy(() => import("./components/page-builder/PageList"));
const PageBuilderLayout = lazy(() => import("./components/page-builder/PageBuilderLayout"));
const EmailSettingsPage = lazy(() => import("./pages/admin/EmailSettingsPage"));
const NumberingSeriesPage = lazy(() => import("./pages/admin/NumberingSeriesPage"));
const NotFound = lazy(() => import("./pages/NotFound"));

function LoadingSpinner() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ConfirmProvider>
          <BrowserRouter>
            <Suspense fallback={<LoadingSpinner />}>
              <Routes>
                {/* Public routes */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />

                {/* Protected routes */}
                <Route element={<ProtectedRoute />}>
                  <Route path="/app" element={<AppLayout />}>
                    <Route index element={<Navigate to="/app/dashboard" replace />} />
                    <Route path="dashboard" element={<Dashboard />} />
                    <Route path="financial/*" element={<Dashboard />} />
                    <Route path="assets/*" element={<Dashboard />} />
                    <Route path="treasury/*" element={<Dashboard />} />
                    <Route path="scm/*" element={<Dashboard />} />
                    <Route path="crm/*" element={<Dashboard />} />
                    <Route path="mrp/*" element={<Dashboard />} />
                    <Route path="hrm/*" element={<Dashboard />} />
                    <Route path="admin" element={<Dashboard />} />
                    <Route path="admin/users" element={<UserListPage />} />
                    <Route path="admin/users/new" element={<UserFormPage />} />
                    <Route path="admin/users/:id" element={<UserFormPage />} />
                    <Route path="admin/page-builder" element={<PageList />} />
                    <Route path="admin/page-builder/new" element={<PageBuilderLayout />} />
                    <Route path="admin/page-builder/:pageKey" element={<PageBuilderLayout />} />
                    <Route path="admin/settings" element={<EmailSettingsPage />} />
                    <Route path="admin/numbering-series" element={<NumberingSeriesPage />} />
                  </Route>
                </Route>

                {/* Redirects */}
                <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </ConfirmProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
