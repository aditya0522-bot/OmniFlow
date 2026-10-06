import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import Logo from "../components/Logo";

export default function Signup() {
  const { user, signup } = useAuth();
  const { t, toggle } = useI18n();
  const [form, setForm] = useState({ company: "", name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signup(form);
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
          <h2>{t.login.signupTitle}</h2>
          <label className="field">
            <span>{t.login.company}</span>
            <input value={form.company} onChange={set("company")} required minLength={2} maxLength={120} autoFocus />
          </label>
          <label className="field">
            <span>{t.login.yourName}</span>
            <input value={form.name} onChange={set("name")} required maxLength={120} autoComplete="name" />
          </label>
          <label className="field">
            <span>{t.login.email}</span>
            <input type="email" value={form.email} onChange={set("email")} required autoComplete="username" />
          </label>
          <label className="field">
            <span>{t.login.password}</span>
            <input type="password" value={form.password} onChange={set("password")} required minLength={8} autoComplete="new-password" />
            <small>{t.login.passwordHint}</small>
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="btn primary wide" disabled={busy}>
            {busy ? t.login.creating : t.login.createAccount}
          </button>
          <p className="alt-link">
            <Link to="/login" className="link">{t.login.haveAccount}</Link>
          </p>
        </form>
      </section>
    </div>
  );
}
