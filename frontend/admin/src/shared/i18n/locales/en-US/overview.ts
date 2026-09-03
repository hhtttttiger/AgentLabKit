export const overview = {
  greeting: 'Good {{time}}',
  subtitle: 'What do you want to do?',
  actions: {
    testAgent: 'Test an Agent',
    createAgent: 'Create Agent',
  },
  metrics: {
    agents: 'Agents',
    runs: 'Runs',
    evaluation: 'Evaluation',
    cost: 'Cost',
    noData: 'No data yet',
    noRuns: 'No runs yet',
    totalRuns: 'Total runs',
    manageAgents: 'Manage agents',
    evaluationUnavailable: 'Evaluation data is not available yet.',
    costComingSoon: 'Coming soon',
  },
  recentRuns: {
    title: 'Recent Runs',
    empty: 'No runs yet. Runs will appear here after you test or execute an Agent.',
    openPlayground: 'Open Playground',
    viewAll: 'View all runs',
  },
  needsAttention: {
    title: 'Needs Attention',
    empty: 'No issues detected',
  },
} as const;
