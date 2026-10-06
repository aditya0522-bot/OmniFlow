import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { useLoad } from "../util";
import Logo from "../components/Logo";

export default function Login() {
  const { user, login } = useAuth();
  const { t, toggle } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const config = useLoad(() => api("/public/config"), []);

  if (user) return <Navigate to="/dashboard" replace />;

  const submit = async (e, creds = { email, password }) => {
    e?.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(creds.email, creds.password);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <section className="login-art">
        <div className="brand">
          <Logo size={36} />
          <span>OmniFlow</span>
        </div>
        <div>
          <h1>{t.login.headline}</h1>
          <p>{t.login.text}</p>
        </div>
      </section>

      <section className="login-form">
        <button className="btn ghost lang-corner" onClick={toggle}>
          {t.common.switchLang}
        </button>
        <form onSubmit={submit}>
          <h2>{t.login.title}</h2>

          <label className="field">
            <span>{t.login.email}</span>
            <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          </label>
          <label className="field">
            <span>{t.login.password}</span>
            <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>

          {error && <p className="form-error" role="alert">{error}</p>}

          <button className="btn primary wide" disabled={busy}>
            {busy ? t.login.submitting : t.login.submit}
          </button>

          {config.data?.allow_signup !== false && (
            <p className="alt-link">
              <Link to="/signup" className="link">{t.login.createWorkspace}</Link>
            </p>
          )}

          {config.data?.demo_mode && (
            <button
              type="button"
              className="btn ghost wide demo-btn"
              disabled={busy}
              onClick={() => submit(null, { email: config.data.demo_email, password: config.data.demo_password })}
            >
              {t.login.tryDemo}
            </button>
          )}

          {import.meta.env.DEV && !config.data?.demo_mode && (
            <button
              type="button"
              className="demo-hint"
              onClick={() => {
                setEmail("admin@omniflow.local");
                setPassword("admin123");
              }}
            >
              {t.login.demo}: admin@omniflow.local / admin123
            </button>
          )}
        </form>
      </section>
    </div>
  );
}
