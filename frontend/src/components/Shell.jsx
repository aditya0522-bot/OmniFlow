import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Inbox, Users, ShoppingBag, Bot, UserCog, Settings, LogOut, Languages } from "lucide-react";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import Logo from "./Logo";
import Avatar from "./Avatar";

const items = [
  { to: "/dashboard", key: "dashboard", icon: LayoutDashboard },
  { to: "/inbox", key: "inbox", icon: Inbox },
  { to: "/customers", key: "customers", icon: Users },
  { to: "/orders", key: "orders", icon: ShoppingBag },
  { to: "/bot", key: "bot", icon: Bot, admin: true },
  { to: "/team", key: "team", icon: UserCog, admin: true },
  { to: "/settings", key: "settings", icon: Settings },
];

export default function Shell() {
  const { user, isAdmin, logout } = useAuth();
  const { t, toggle } = useI18n();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Logo />
          <span>OmniFlow</span>
        </div>

        <nav aria-label="Main">
          {items.filter((item) => isAdmin || !item.admin).map(({ to, key, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "nav active" : "nav")}>
              <Icon size={19} strokeWidth={1.9} />
              <span>{t.nav[key]}</span>
            </NavLink>
          ))}
        </nav>

        <div className="side-foot">
          <button className="nav" onClick={toggle}>
            <Languages size={19} strokeWidth={1.9} />
            <span>{t.common.switchLang}</span>
          </button>
          <div className="me">
            <Avatar name={user.name} size="sm" />
            <div>
              <b>{user.name}</b>
              <small>{user.tenant.name}</small>
            </div>
            <button className="icon-btn on-dark" onClick={logout} aria-label={t.common.signOut} title={t.common.signOut}>
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
