import { useQuery } from '@tanstack/react-query'
import { getRecommendations } from '../api/client'

export function useRecommendations({ storeId, itemId } = {}) {
  return useQuery({
    queryKey: ['recommendations', storeId, itemId],
    queryFn: () => getRecommendations({ storeId, itemId }),
  })
}
