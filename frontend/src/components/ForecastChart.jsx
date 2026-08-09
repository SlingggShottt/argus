import { useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useForecastData } from '../hooks/useForecastData'

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded border border-hairline bg-surface px-3 py-2 text-sm shadow-sm">
      <div className="text-ink-muted">{label}</div>
      <div className="text-ink-primary font-medium tabular-nums">
        {payload[0].value.toFixed(1)} units
      </div>
    </div>
  )
}

export function ForecastChart() {
  const [storeId, setStoreId] = useState(1)
  const [itemId, setItemId] = useState(1)
  const { data, isLoading, isError } = useForecastData(storeId, itemId)

  return (
    <div className="rounded-lg border border-hairline bg-surface p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-ink-primary">Demand Forecast</h2>
        <div className="flex items-center gap-2 text-sm text-ink-secondary">
          <label className="flex items-center gap-1">
            Store
            <input
              type="number"
              min={1}
              max={10}
              value={storeId}
              onChange={(e) => setStoreId(Number(e.target.value))}
              className="w-14 border border-hairline rounded px-1.5 py-0.5 bg-surface text-ink-primary"
            />
          </label>
          <label className="flex items-center gap-1">
            Item
            <input
              type="number"
              min={1}
              max={50}
              value={itemId}
              onChange={(e) => setItemId(Number(e.target.value))}
              className="w-14 border border-hairline rounded px-1.5 py-0.5 bg-surface text-ink-primary"
            />
          </label>
        </div>
      </div>

      {isLoading && <p className="text-sm text-ink-muted">Loading...</p>}
      {isError && <p className="text-sm text-status-critical">No forecast found for this store/item.</p>}

      {data && (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--gridline)" />
            <XAxis
              dataKey="forecast_date"
              stroke="var(--baseline)"
              tick={{ fill: 'var(--ink-muted)', fontSize: 12 }}
              tickFormatter={(d) => d.slice(5)}
              minTickGap={24}
            />
            <YAxis stroke="var(--baseline)" tick={{ fill: 'var(--ink-muted)', fontSize: 12 }} width={36} />
            <Tooltip content={<ChartTooltip />} />
            <Line
              type="monotone"
              dataKey="predicted_sales"
              stroke="var(--series-1)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
