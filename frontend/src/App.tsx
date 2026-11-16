import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/queryClient";
import { useAuthStore } from "@/store/auth";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Toaster } from "@/components/ui/toaster";

import Search from "@/pages/Search";
import SailingDetail from "@/pages/SailingDetail";
import Alerts from "@/pages/Alerts";
import Account from "@/pages/Account";
import Billing from "@/pages/Billing";
import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import VerifyEmail from "@/pages/auth/VerifyEmail";

function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

function ProtectedRoute() {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (!accessToken) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route element={<Layout />}>
          {/* Public */}
          <Route index element={<Navigate to="/search" replace />} />
          <Route path="/search" element={<Search />} />
          <Route path="/sailings/:id" element={<SailingDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />

          {/* Protected */}
          <Route element={<ProtectedRoute />}>
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/account" element={<Account />} />
            <Route path="/billing" element={<Billing />} />
          </Route>

          <Route path="*" element={<Navigate to="/search" replace />} />
        </Route>
      </Routes>
      <Toaster />
    </QueryClientProvider>
  );
}
