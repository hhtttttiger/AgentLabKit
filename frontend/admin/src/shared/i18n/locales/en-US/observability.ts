// Auto-generated — do not edit manually
export const observability = {
  label: 'Observability',
  summary: 'View system observability data including traces and metrics.',
  eyebrow: 'Observability',
  title: 'Observability',
  sections: {
    traces: 'Distributed tracing'
  },
  traces: {
    title: 'Distributed tracing',
    description: 'View system request tracing information.',
    searchPlaceholder: 'Search Trace ID...',
    emptyTitle: 'No trace data',
    emptyDescription: 'Trace data will appear here once the system starts processing requests.',
    loadError: 'Failed to load trace data. Please try again.',
    detailLoadError: 'Failed to load trace details. Please try again.',
    timeRange: {
      '24h': '24h',
      '7d': '7 days',
      '30d': '30 days',
    },
    metrics: {
      totalTraces: 'Total Traces',
      avgLatency: 'Avg Latency',
      totalTokens: 'Total Tokens',
      errorCount: 'Errors',
    },
    columns: {
      traceId: 'Trace ID',
      agent: 'Agent',
      operation: 'Operation',
      status: 'Status',
      duration: 'Duration',
      tokens: 'Tokens',
      spanCount: 'Spans',
      startTime: 'Start time',
      services: 'Services',
    },
    status: {
      success: 'Success',
      error: 'Error',
    },
    detail: {
      title: 'Trace details',
      backToList: '← Back to List',
      waterfall: 'Call Chain Waterfall',
      spanList: 'Span List',
      spanAttributes: 'Span Attributes',
      collapse: 'Collapse',
      expand: 'Details',
      noSpanData: 'No span data',
      timeline: 'Timeline',
      spans: 'Spans',
      tags: 'Tags',
      columns: {
        kind: 'Kind',
        name: 'Name',
        status: 'Status',
        duration: 'Duration',
        actions: 'Actions',
      },
    },
  }
} as const;
