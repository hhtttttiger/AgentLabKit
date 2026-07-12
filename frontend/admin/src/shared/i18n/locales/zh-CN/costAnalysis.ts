// Auto-generated — do not edit manually
export const costAnalysis = {
      label: '成本分析',
      summary: '分析模型调用成本、预算和告警。',
      eyebrow: '成本分析',
      title: '成本分析',
      sections: {
        overview: '成本概览',
        budgets: '预算管理',
        alerts: '成本告警'
      },
      overview: {
        totalSpend: '总花费',
        totalRequests: '总请求量',
        totalTokens: '总 Token',
        avgLatency: '平均延迟',
        costTrend: '成本趋势',
        modelDistribution: '模型分布',
        topModels: 'Top 模型',
        error: '加载成本概览失败，请重试。'
      },
      budgets: {
        title: '预算管理',
        description: '设置和管理模型调用预算。',
        createBudget: '创建预算',
        emptyTitle: '暂无预算',
        emptyDescription: '点击"创建预算"开始设置预算限制。',
        error: '加载预算失败，请重试。',
        scope: {
          global: '全范围',
          model: '模型',
          agent: 'Agent',
          user: '用户'
        },
        form: {
          title: '新建预算',
          description: '设置预算限制和告警阈值',
          scopeType: '范围类型',
          scopeKey: '模型',
          monthlyLimit: '月度预算 (USD)',
          alertThreshold: '告警阈值 (%)',
          isEnabled: '启用'
        },
        columns: {
          name: '预算名称',
          limit: '预算上限',
          currentSpend: '当前花费',
          usage: '使用率',
          period: '周期',
          status: '状态',
          actions: '操作'
        },
        status: {
          active: '生效中',
          exceeded: '已超支',
          inactive: '未生效'
        },
        actions: {
          edit: '编辑',
          delete: '删除',
          create: '创建',
          cancel: '取消',
          creating: '创建中...'
        }
      },
      alerts: {
        title: '成本告警',
        description: '配置成本告警规则，当花费超过阈值时通知。',
        createAlert: '创建告警',
        evaluate: '评估告警',
        acknowledge: '确认',
        emptyTitle: '暂无告警',
        emptyDescription: '当前没有触发的告警。',
        error: '加载告警失败，请重试。',
        typeLabel: {
          threshold: '阈值告警',
          exceeded: '超支'
        },
        statusLabel: {
          acknowledged: '已确认',
          pending: '待处理'
        },
        columns: {
          name: '告警名称',
          threshold: '阈值',
          type: '类型',
          status: '状态',
          lastTriggered: '最近触发',
          actions: '操作'
        },
        tableHeaders: {
          type: '类型',
          scope: '范围',
          currentSpend: '当前花费',
          threshold: '阈值',
          triggeredAt: '触发时间',
          status: '状态',
          actions: '操作'
        },
        type: {
          absolute: '绝对值',
          percentage: '百分比'
        },
        status: {
          active: '启用',
          inactive: '停用'
        },
        actions: {
          edit: '编辑',
          delete: '删除'
        }
      }
    } as const;
