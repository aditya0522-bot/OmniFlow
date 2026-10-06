import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageCircle, Plus, Search, Trash2 } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { formatPhone, shortDate, useDebounced, useLoad } from "../util";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";
import StateBox from "../components/StateBox";

export default function Customers() {
  const { t, lang } = useI18n();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const q = useDebounced(query);
  const { data, loading, error, reload } = useLoad(() => api(`/customers?q=${encodeURIComponent(q)}`), [q]);

  const openChat = async (customer) => {
    const conversation = await api(`/customers/${customer.id}/conversation`, { method: "POST" });
    navigate(`/inbox/${conversation.id}`);
  };

  const remove = async (customer) => {
    if (!window.confirm(t.customers.confirmDelete)) return;
    await api(`/customers/${customer.id}`, { method: "DELETE" });
    reload();
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>{t.nav.customers}</h1>
        </div>
        <button className="btn primary" onClick={() => setAdding(true)}>
          <Plus size={17} />
          {t.customers.add}
        </button>
      </header>

      <label className="search wide-search">
        <Search size={17} />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t.inbox.searchPlaceholder} />
      </label>

      <StateBox loading={loading} error={error} onRetry={reload}>
        {data && data.length === 0 ? (
          <p className="state">{q ? t.common.nothingFound : t.customers.empty}</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t.customers.name}</th>
                  <th>{t.customers.phone}</th>
                  <th className="num">{t.customers.orders}</th>
                  <th>{t.customers.since}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data?.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <div className="who">
                        <Avatar name={c.name} size="sm" />
                        <span className="strong">{c.name}</span>
                        {c.opted_out && <span className="pill cancelled">{t.customers.optedOutTag}</span>}
                      </div>
                    </td>
                    <td>{formatPhone(c.phone)}</td>
                    <td className="num">{c.order_count}</td>
                    <td>{shortDate(c.created_at, lang)}</td>
                    <td className="actions">
                      <button className="btn ghost small" onClick={() => openChat(c)}>
                        <MessageCircle size={15} />
                        {t.customers.chat}
                      </button>
                      {isAdmin && (
                        <button className="icon-btn" onClick={() => remove(c)} aria-label={t.customers.delete} title={t.customers.delete}>
                          <Trash2 size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </StateBox>

      {adding && (
        <NewCustomer
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            reload();
          }}
        />
      )}
    </div>
  );
}

function NewCustomer({ onClose, onSaved }) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/customers", { method: "POST", body: { name, phone, consent } });
      onSaved();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Modal title={t.customers.newTitle} onClose={onClose}>
      <form onSubmit={submit}>
        <label className="field">
          <span>{t.customers.name}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
        </label>
        <label className="field">
          <span>{t.customers.phone}</span>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" required />
          <small>{t.customers.phoneHint}</small>
        </label>
        <label className="check">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required />
          <span>{t.customers.consent}</span>
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>{t.common.cancel}</button>
          <button className="btn primary" disabled={busy}>{t.customers.save}</button>
        </div>
      </form>
    </Modal>
  );
}
