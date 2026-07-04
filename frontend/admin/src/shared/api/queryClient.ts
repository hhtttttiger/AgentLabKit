import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: true, // re-validate on tab return — cheapest refresh
      retry: 1,                   // retry once on failure, then surface the error
    },
    mutations: {
      retry: 0, // never retry mutations — avoid duplicate side effects
    },
  },
});
