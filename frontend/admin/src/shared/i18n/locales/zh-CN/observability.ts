// Auto-generated — do not edit manually
export const observability = {
      label: '可观测性',
      summary: '查看系统可观测性数据，包括链路追踪和指标。',
      eyebrow: '可观测性',
      title: '可观测性',
      sections: {
        traces: '链路追踪'
      },
      traces: {
        title: '链路追踪',
        description: '查看系统请求链路追踪信息。',
        searchPlaceholder: '搜索 Trace ID...',
        emptyTitle: '暂无追踪数据',
        emptyDescription: '系统开始处理请求后，追踪数据将出现在这里。',
        loadError: '加载追踪数据失败，请重试。',
        detailLoadError: '加载追踪详情失败，请重试。',
        timeRange: {
          '24h': '24小时',
          '7d': '7 天',
          '30d': '30 天',
        },
        metrics: {
          totalTraces: '总 Trace 数',
          avgLatency: '平均延迟',
          totalTokens: '总 Token',
          errorCount: '错误数',
        },
        columns: {
          traceId: 'Trace ID',
          agent: 'Agent',
          operation: '操作',
          status: '状态',
          duration: '耗时',
          tokens: 'Token',
          spanCount: 'Span 数',
          startTime: '开始时间',
          services: '服务数',
        },
        status: {
          success: '成功',
          error: '失败',
        },
        detail: {
          title: '追踪详情',
          backToList: '← 返回列表',
          waterfall: '调用链路 Waterfall',
          spanList: 'Span 列表',
          spanAttributes: 'Span 属性',
          collapse: '收起',
          expand: '详情',
          noSpanData: '无 Span 数据',
          timeline: '时间线',
          spans: '跨度',
          tags: '标签',
          columns: {
            kind: '类型',
            name: '名称',
            status: '状态',
            duration: '耗时',
            actions: '操作',
          },
        },
      }
    } as const;
