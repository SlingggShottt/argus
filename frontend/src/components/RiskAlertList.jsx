import { useState } from 'react'
import { useRisks } from '../hooks/useRisks'

// Status color never carries meaning alone -- icon + label pairing per the
// dataviz skill's status-palette rule.
function SeverityBadge({ severity }) {
  const isHigh = severity === 'high'
  const color = isHigh ? 'bg-status-critical' : 'bg-status-warning'
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-primary">
      <span className={`inline-block h-2 w-2 rounded-full ${color}`} aria-hidden="true" />
      {isHigh ? 'High' : 'Medium'}
    </span>
  )
}

export function RiskAlertList() {
  const [riskType, setRiskType] = useState('')
  const [severity, setSeverity] = useState('')
  const { data, isLoading, isError } = useRisks({ riskType, severity })

  return (
    <div className="rounded-lg border border-hairline bg-surface p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-ink-primary">Risk Alerts</h2>
        <div className="flex gap-2">
          <select
            className="text-sm border border-hairline rounded px-2 py-1 bg-surface text-ink-primary"
            value={riskType}
            onChange={(e) => setRiskType(e.target.value)}
          >
            <option value="">All types</option>
            <option value="stockout">Stockout</option>
            <option value="anomaly">Anomaly</option>
          </select>
          <select
            className="text-sm border border-hairline rounded px-2 py-1 bg-surface text-ink-primary"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            <option value="">All severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
          </select>
        </div>
      </div>

      {isLoading && <p className="text-sm text-ink-muted">Loading...</p>}
      {isError && <p className="text-sm text-status-critical">Failed to load risk flags.</p>}

      {data && (
        <div className="overflow-x-auto max-h-80">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="text-ink-muted border-b border-gridline">
                <th className="py-1.5 pr-3 font-medium">Store</th>
                <th className="py-1.5 pr-3 font-medium">Item</th>
                <th className="py-1.5 pr-3 font-medium">Type</th>
                <th className="py-1.5 pr-3 font-medium">Severity</th>
                <th className="py-1.5 font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((row) => (
                <tr key={`${row.store_id}-${row.item_id}-${row.risk_type}`} className="border-b border-gridline">
                  <td className="py-1.5 pr-3 text-ink-primary">{row.store_id}</td>
                  <td className="py-1.5 pr-3 text-ink-primary">{row.item_id}</td>
                  <td className="py-1.5 pr-3 text-ink-secondary capitalize">{row.risk_type}</td>
                  <td className="py-1.5 pr-3">
                    <SeverityBadge severity={row.severity} />
                  </td>
                  <td className="py-1.5 text-ink-secondary">{row.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.data.length === 0 && <p className="text-sm text-ink-muted py-2">No risk flags match this filter.</p>}
        </div>
      )}
    </div>
  )
}
