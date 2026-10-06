import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { formatPhone, money, shortDate, clock, useDebounced, useLoad } from "../util";
import Modal from "../components/Modal";
import StateBox from "../components/StateBox";

const STATES = ["received", "preparing", "out_for_delivery", "delivered", "cancelled"];

export default function Orders() {
  const { t, lang } = useI18n();
  const [state, setState] = useState("all");
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const q = useDebounced(query);
  const { data, loading, error, reload, setData } = useLoad(
    () => api(`/orders?state=${state}&q=${encodeURIComponent(q)}`),
    [state, q],
    15000
  );

  const changeStatus = async (order, next) => {
    const updated = await api(`/orders/${order.id}`, { method: "PATCH", body: { status: next } });
    setData((list) => list.map((o) => (o.id === order.id ? updated : o)));
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>{t.nav.orders}</h1>
        </div>
        <button className="btn primary" onClick={() => setAdding(true)}>
          <Plus size={17} />
          {t.orders.add}
        </button>
      </header>

      <div className="toolbar">
        <div className="tabs">
          {["all", ...STATES].map((key) => (
            <button key={key} className={state === key ? "tab on" : "tab"} onClick={() => setState(key)}>
              {key === "all" ? t.common.all : t.orders.states[key]}
            </button>
          ))}
        </div>
        <label className="search">
          <Search size={17} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t.orders.searchPlaceholder} />
        </label>
      </div>

      <StateBox loading={loading} error={error} onRetry={reload}>
        {data && data.length === 0 ? (
          <p className="state">{q || state !== "all" ? t.common.nothingFound : t.orders.empty}</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t.orders.code}</th>
                  <th>{t.orders.customer}</th>
                  <th>{t.orders.items}</th>
                  <th className="num">{t.orders.amount}</th>
                  <th>{t.orders.placed}</th>
                  <th>{t.orders.status}</th>
                </tr>
              </thead>
              <tbody>
                {data?.map((o) => (
                  <tr key={o.id}>
                    <td className="strong">{o.code}</td>
                    <td>
                      {o.customer.name}
                      <small className="sub">{formatPhone(o.customer.phone)}</small>
                    </td>
                    <td>{o.items}</td>
                    <td className="num">{money(o.amount, lang)}</td>
                    <td>
                      {shortDate(o.created_at, lang)}
                      <small className="sub">{clock(o.created_at, lang)}</small>
                    </td>
                    <td>
                      <select
                        className={`pill-select ${o.status}`}
                        value={o.status}
                        onChange={(e) => changeStatus(o, e.target.value)}
                        aria-label={t.orders.status}
                      >
                        {STATES.map((s) => (
                          <option key={s} value={s}>{t.orders.states[s]}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </StateBox>

      {adding && (
        <NewOrder
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

function NewOrder({ onClose, onSaved }) {
  const { t } = useI18n();
  const customers = useLoad(() => api("/customers"), []);
  const [customerId, setCustomerId] = useState("");
  const [items, setItems] = useState("");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/orders", {
        method: "POST",
        body: { customer_id: Number(customerId), items, amount: Number(amount) },
      });
      onSaved();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Modal title={t.orders.newTitle} onClose={onClose}>
      <form onSubmit={submit}>
        <label className="field">
          <span>{t.orders.customer}</span>
          <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
            <option value="">{t.orders.selectCustomer}</option>
            {customers.data?.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{t.orders.items}</span>
          <input value={items} onChange={(e) => setItems(e.target.value)} required />
        </label>
        <label className="field">
          <span>{t.orders.amount}</span>
          <input type="number" min="0" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>{t.common.cancel}</button>
          <button className="btn primary" disabled={busy}>{t.orders.save}</button>
        </div>
      </form>
    </Modal>
  );
}
