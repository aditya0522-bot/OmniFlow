import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { useI18n } from "./i18n";
import Shell from "./components/Shell";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Inbox from "./pages/Inbox";
import Customers from "./pages/Customers";
import Orders from "./pages/Orders";
import Autoreplies from "./pages/Autoreplies";
import Signup from "./pages/Signup";
import Team from "./pages/Team";
import Settings from "./pages/Settings";

function RequireAuth({ children }) {
  const { user, ready } = useAuth();
  const { t } = useI18n();
  if (!ready) return <p className="state">{t.common.loading}</p>;
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        element={
          <RequireAuth>
            <Shell />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="inbox/:id" element={<Inbox />} />
        <Route path="customers" element={<Customers />} />
        <Route path="orders" element={<Orders />} />
        <Route path="bot" element={<Autoreplies />} />
        <Route path="team" element={<Team />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
