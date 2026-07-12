// Auto-generated — do not edit manually
export const modelMonitoring = {
  label: 'Model monitoring',
  summary: 'Review usage metrics and call errors by model.',
  eyebrow: 'AI Model Center',
  title: 'Model monitoring',
  sections: {
    overview: 'Overview',
    errors: 'Errors'
  },
  overview: {
    emptyTitle: 'No monitoring data',
    emptyDescription: 'Monitoring data will appear here after models start receiving traffic.',
    metrics: {
      totalRequests: 'Total requests',
      totalTokens: 'Total tokens',
      averageLatency: 'Average latency',
      totalErrors: 'Total errors'
    },
    hints: {
      totalRequests: 'Total requests across all models.',
      totalTokens: 'Combined input and output token volume.',
      averageLatency: 'Request-weighted average response time.',
      totalErrors: 'Total error count across all models.'
    },
    card: {
      requests: '{{value}} requests',
      tokens: '{{value}} tokens',
      errors: '{{value}} errors'
    }
  },
  usage: {
    viewToggle: {
      list: 'List',
      card: 'Card'
    },
    filters: {
      model: 'Model',
      allModels: 'All models',
      loading: 'Loading...',
      startTime: 'Start time',
      endTime: 'End time'
    },
    metrics: {
      totalRequests: 'Total requests',
      totalTokens: 'Total tokens',
      averageLatency: 'Average latency',
      totalErrors: 'Total errors'
    },
    table: {
      headers: {
        modelName: 'Model name',
        requests: 'Requests',
        inputTokens: 'Input tokens',
        outputTokens: 'Output tokens',
        averageLatency: 'Avg latency',
        errorRate: 'Error rate'
      }
    },
    detail: {
      drawerTitle: 'Request detail',
      filters: {
        startTime: 'Start time',
        endTime: 'End time'
      },
      table: {
        headers: {
          startedAt: 'Start time',
          requestId: 'Request ID',
          capability: 'Capability',
          attempts: 'Attempts',
          inputTokens: 'Input tokens',
          outputTokens: 'Output tokens',
          latency: 'Duration',
          result: 'Result'
        },
        status: {
          success: 'Success',
          failure: 'Failed'
        }
      },
      empty: {
        title: 'No request records',
        description: 'No requests found in the selected time range.'
      }
    },
    empty: {
      title: 'No usage data',
      description: 'Usage data will appear here after models start receiving traffic.'
    },
    error: 'Failed to load usage data. Please try again.',
    grid: {
      empty: {
        title: 'No monitoring data',
        description: 'Monitoring data will appear here after models start receiving traffic.'
      },
      error: 'Failed to load monitoring data.',
      requests: '{{value}} requests',
      errors: '{{value}} errors'
    }
  },
  errors: {
    filters: {
      model: 'Model',
      allModels: 'All models',
      loading: 'Loading...',
      errorCode: 'Error code',
      allErrorCodes: 'All error codes',
      startTime: 'Start time',
      endTime: 'End time'
    },
    errorCodeLabels: {
      UPSTREAM_FAILURE: 'Upstream failure',
      upstream_error: 'Upstream error',
      provider_timeout: 'Provider timeout',
      provider_rate_limited: 'Rate limited',
      provider_auth_failed: 'Authentication failed',
      unsupported_capability: 'Unsupported capability',
      validation_error: 'Validation error',
      session_closed: 'Session closed'
    },
    table: {
      headers: {
        time: 'Time',
        model: 'Model',
        errorCode: 'Error code',
        capability: 'Capability',
        errorMessage: 'Error message'
      },
      uncategorized: 'Uncategorized error'
    },
    detail: {
      errorMessage: 'Error message',
      instance: 'Instance',
      capability: 'Capability',
      duration: 'Request duration'
    },
    empty: {
      title: 'No error records',
      description: 'No matching call errors found — great news!'
    },
    error: 'Failed to load error records. Please try again.'
  }
} as const;
