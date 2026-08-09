import { ChatPanel } from './components/ChatPanel'
import { ForecastChart } from './components/ForecastChart'
import { KpiCard } from './components/KpiCard'
import { RecommendationTable } from './components/RecommendationTable'
import { RiskAlertList } from './components/RiskAlertList'
import { useRecommendations } from './hooks/useRecommendations'
import { useRisks } from './hooks/useRisks'

function KpiRow() {
  const { data: risks } = useRisks()
  const { data: recommendations } = useRecommendations()

  const highCount = risks?.data.filter((r) => r.severity === 'high').length ?? '–'
  const mediumCount = risks?.data.filter((r) => r.severity === 'medium').length ?? '–'
  const recommendationCount = recommendations?.meta.count ?? '–'

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      <KpiCard label="High-Risk SKUs" value={highCount} sublabel="Will stock out before reorder arrives" />
      <KpiCard label="Medium-Risk SKUs" value={mediumCount} sublabel="Dangerously close to stockout" />
      <KpiCard label="Reorder Recommendations" value={recommendationCount} sublabel="Across all SKUs" />
    </div>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-page">
      <header className="border-b border-hairline bg-surface px-6 py-4">
        <h1 className="text-xl font-semibold text-ink-primary">Argus</h1>
        <p className="text-sm text-ink-secondary">Demand forecasting & inventory risk dashboard</p>
      </header>

      <main className="max-w-6xl mx-auto p-6 flex flex-col gap-4">
        <KpiRow />

        <div className="grid md:grid-cols-2 gap-4">
          <ForecastChart />
          <ChatPanel />
        </div>

        <RiskAlertList />
        <RecommendationTable />
      </main>
    </div>
  )
}

export default App
