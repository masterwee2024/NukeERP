import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { ConfirmProvider } from "./components/ui/ConfirmDialog";
import AppLayout from "./components/Layout/AppLayout";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Login = lazy(() => import("./pages/Login"));
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
      <ConfirmProvider>
        <BrowserRouter>
          <Suspense fallback={<LoadingSpinner />}>
            <Routes>
              <Route path="/login" element={<Login />} />
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
                <Route path="admin/*" element={<Dashboard />} />
              </Route>
              <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ConfirmProvider>
    </QueryClientProvider>
  );
}
