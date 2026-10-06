import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { money, useLoad, weekday, shortDate } from "../util";
import StateBox from "../components/StateBox";

export default function Dashboard() {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const { data, loading, error, reload } = useLoad(() => api("/dashboard"), [], 20000);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>{t.nav.dashboard}</h1>
          <p>{user.tenant.name}</p>
        </div>
      </header>

      <StateBox loading={loading} error={error} onRetry={reload}>
        {data && (
          <>
            <section className="stat-strip">
              <Link to="/inbox" className="stat">
                <span>{t.dashboard.open}</span>
                <b>{data.open_conversations}</b>
              </Link>
              <Link to="/inbox" className="stat">
                <span>{t.dashboard.unread}</span>
                <b>{data.unread_messages}</b>
              </Link>
              <Link to="/orders" className="stat">
                <span>{t.dashboard.ordersToday}</span>
                <b>{data.orders_today}</b>
              </Link>
              <div className="stat">
                <span>{t.dashboard.revenueToday}</span>
                <b>{money(data.revenue_today, lang)}</b>
              </div>
            </section>

            <div className="split">
              <section className="panel">
                <div className="panel-head">
                  <h2>{t.dashboard.weekTitle}</h2>
                  <div className="legend">
                    <span><i className="dot light" />{t.dashboard.incoming}</span>
                    <span><i className="dot deep" />{t.dashboard.outgoing}</span>
                  </div>
                </div>
                <WeekChart week={data.week} lang={lang} />
              </section>

              <section className="panel">
                <div className="panel-head">
                  <h2>{t.dashboard.statusTitle}</h2>
                </div>
                <StatusBars counts={data.order_status} labels={t.orders.states} />
              </section>
            </div>

            <section className="panel">
              <div className="panel-head">
                <h2>{t.dashboard.recent}</h2>
                <Link to="/orders" className="link">{t.dashboard.viewAll}</Link>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t.orders.code}</th>
                      <th>{t.orders.customer}</th>
                      <th>{t.orders.items}</th>
                      <th className="num">{t.orders.amount}</th>
                      <th>{t.orders.status}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_orders.map((o) => (
                      <tr key={o.id}>
                        <td className="strong">{o.code}</td>
                        <td>{o.customer.name}</td>
                        <td>{o.items}</td>
                        <td className="num">{money(o.amount, lang)}</td>
                        <td><span className={`pill ${o.status}`}>{t.orders.states[o.status]}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </StateBox>
    </div>
  );
}

function WeekChart({ week, lang }) {
  const max = Math.max(1, ...week.flatMap((d) => [d.incoming, d.outgoing]));
  return (
    <div className="chart" role="img" aria-label="Messages per day for the last 7 days">
      {week.map((d) => (
        <div className="chart-day" key={d.date}>
          <div className="chart-bars">
            <span className="bar light" style={{ height: `${(d.incoming / max) * 100}%` }} title={`${d.incoming}`} />
            <span className="bar deep" style={{ height: `${(d.outgoing / max) * 100}%` }} title={`${d.outgoing}`} />
          </div>
          <small>{weekday(d.date, lang)}</small>
          <em className="sr-only">{shortDate(d.date, lang)}</em>
        </div>
      ))}
    </div>
  );
}

function StatusBars({ counts, labels }) {
  const max = Math.max(1, ...Object.values(counts));
  return (
    <ul className="hbars">
      {Object.entries(counts).map(([key, count]) => (
        <li key={key}>
          <span>{labels[key]}</span>
          <div className="track">
            <div className={`fill ${key}`} style={{ width: `${(count / max) * 100}%` }} />
          </div>
          <b>{count}</b>
        </li>
      ))}
    </ul>
  );
}
