import { useQuery } from '@tanstack/react-query'
import { getForecast } from '../api/client'

// storeId/itemId are numbers or null -- null disables the query (React
// Query's `enabled` flag) so we don't fetch before a SKU is selected.
export function useForecastData(storeId, itemId) {
  return useQuery({
    queryKey: ['forecast', storeId, itemId],
    queryFn: () => getForecast(storeId, itemId),
    enabled: storeId != null && itemId != null,
  })
}
