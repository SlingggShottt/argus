import { useRecommendations } from '../hooks/useRecommendations'

export function RecommendationTable() {
  const { data, isLoading, isError } = useRecommendations()

  return (
    <div className="rounded-lg border border-hairline bg-surface p-4">
      <h2 className="text-base font-semibold text-ink-primary mb-3">Reorder Recommendations</h2>

      {isLoading && <p className="text-sm text-ink-muted">Loading...</p>}
      {isError && <p className="text-sm text-status-critical">Failed to load recommendations.</p>}

      {data && (
        <div className="overflow-x-auto max-h-80">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="text-ink-muted border-b border-gridline">
                <th className="py-1.5 pr-3 font-medium">Store</th>
                <th className="py-1.5 pr-3 font-medium">Item</th>
                <th className="py-1.5 pr-3 font-medium text-right">Reorder Point</th>
                <th className="py-1.5 font-medium text-right">Reorder Qty</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((row) => (
                <tr key={`${row.store_id}-${row.item_id}`} className="border-b border-gridline">
                  <td className="py-1.5 pr-3 text-ink-primary">{row.store_id}</td>
                  <td className="py-1.5 pr-3 text-ink-primary">{row.item_id}</td>
                  <td className="py-1.5 pr-3 text-right text-ink-primary tabular-nums">
                    {row.reorder_point.toFixed(1)}
                  </td>
                  <td className="py-1.5 text-right text-ink-primary tabular-nums">
                    {row.reorder_quantity.toFixed(1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
