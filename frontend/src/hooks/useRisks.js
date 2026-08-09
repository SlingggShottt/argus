import { useQuery } from '@tanstack/react-query'
import { getRisks } from '../api/client'

export function useRisks({ riskType, severity } = {}) {
  return useQuery({
    queryKey: ['risks', riskType, severity],
    queryFn: () => getRisks({ riskType, severity }),
  })
}
