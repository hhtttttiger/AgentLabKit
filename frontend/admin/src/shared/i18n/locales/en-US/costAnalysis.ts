// Auto-generated — do not edit manually
export const costAnalysis = {
  label: 'Cost analysis',
  summary: 'Analyze model invocation costs, budgets, and alerts.',
  eyebrow: 'Cost analysis',
  title: 'Cost analysis',
  sections: {
    overview: 'Cost overview',
    budgets: 'Budget management',
    alerts: 'Cost alerts'
  },
  overview: {
    totalSpend: 'Total spend',
    totalRequests: 'Total requests',
    totalTokens: 'Total tokens',
    avgLatency: 'Average latency',
    costTrend: 'Cost trend',
    modelDistribution: 'Model distribution',
    topModels: 'Top models',
    error: 'Failed to load cost overview. Please try again.'
  },
  budgets: {
    title: 'Budget management',
    description: 'Set and manage model invocation budgets.',
    createBudget: 'Create budget',
    emptyTitle: 'No budgets',
    emptyDescription: 'Click "Create budget" to start setting budget limits.',
    error: 'Failed to load budgets. Please try again.',
    scope: {
      global: 'Global',
      model: 'Model',
      agent: 'Agent',
      user: 'User'
    },
    form: {
      title: 'Create Budget',
      description: 'Set budget limit and alert threshold',
      scopeType: 'Scope Type',
      scopeKey: 'Model',
      monthlyLimit: 'Monthly Budget (USD)',
      alertThreshold: 'Alert Threshold (%)',
      isEnabled: 'Enabled'
    },
    columns: {
      name: 'Budget name',
      limit: 'Budget limit',
      currentSpend: 'Current spend',
      usage: 'Usage',
      period: 'Period',
      status: 'Status',
      actions: 'Actions'
    },
    status: {
      active: 'Active',
      exceeded: 'Exceeded',
      inactive: 'Inactive'
    },
    actions: {
      edit: 'Edit',
      delete: 'Delete',
      create: 'Create',
      cancel: 'Cancel',
      creating: 'Creating...'
    }
  },
  alerts: {
    title: 'Cost alerts',
    description: 'Configure cost alert rules to notify when spending exceeds thresholds.',
    createAlert: 'Create alert',
    evaluate: 'Evaluate Alerts',
    acknowledge: 'Acknowledge',
    emptyTitle: 'No alerts',
    emptyDescription: 'No triggered alerts at the moment.',
    error: 'Failed to load alerts. Please try again.',
    typeLabel: {
      threshold: 'Threshold Alert',
      exceeded: 'Over Budget'
    },
    statusLabel: {
      acknowledged: 'Acknowledged',
      pending: 'Pending'
    },
    columns: {
      name: 'Alert name',
      threshold: 'Threshold',
      type: 'Type',
      status: 'Status',
      lastTriggered: 'Last triggered',
      actions: 'Actions'
    },
    tableHeaders: {
      type: 'Type',
      scope: 'Scope',
      currentSpend: 'Current Spend',
      threshold: 'Threshold',
      triggeredAt: 'Triggered At',
      status: 'Status',
      actions: 'Actions'
    },
    type: {
      absolute: 'Absolute',
      percentage: 'Percentage'
    },
    status: {
      active: 'Active',
      inactive: 'Inactive'
    },
    actions: {
      edit: 'Edit',
      delete: 'Delete'
    }
  }
} as const;
