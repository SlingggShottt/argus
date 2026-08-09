// Presentational stat tile. Large standalone figures use proportional
// (default) numerals per the dataviz skill's typography guidance.

export function KpiCard({ label, value, sublabel }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface p-4 flex flex-col gap-1">
      <span className="text-sm text-ink-muted">{label}</span>
      <span className="text-3xl font-semibold text-ink-primary">{value}</span>
      {sublabel && <span className="text-xs text-ink-secondary">{sublabel}</span>}
    </div>
  )
}
