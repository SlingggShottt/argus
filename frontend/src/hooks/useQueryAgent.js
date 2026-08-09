import { useMutation } from '@tanstack/react-query'
import { postQuery } from '../api/client'

// A mutation, not a query -- each chat message is a one-off POST, not
// cached/refetched data.
export function useQueryAgent() {
  return useMutation({
    mutationFn: (question) => postQuery(question),
  })
}
