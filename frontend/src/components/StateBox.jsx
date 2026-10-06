import { useI18n } from "../i18n";

export default function StateBox({ loading, error, onRetry, children }) {
  const { t } = useI18n();
  if (loading) return <p className="state">{t.common.loading}</p>;
  if (error) {
    return (
      <div className="state error">
        <p>{error}</p>
        {onRetry && (
          <button className="btn ghost" onClick={onRetry}>
            {t.common.retry}
          </button>
        )}
      </div>
    );
  }
  return children;
}
