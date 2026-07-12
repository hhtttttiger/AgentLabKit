// Auto-generated — do not edit manually
export const modelMonitoring = {
      label: '模型监控',
      summary: '按模型卡片维度查看用量统计和调用错误。',
      eyebrow: 'AI 模型中心',
      title: '模型监控',
      sections: {
        overview: '概览',
        errors: '调用错误'
      },
      overview: {
        emptyTitle: '暂无监控数据',
        emptyDescription: '当模型开始接收请求后，监控数据将会出现在这里。',
        metrics: {
          totalRequests: '总请求量',
          totalTokens: '总 Token',
          averageLatency: '平均延迟',
          totalErrors: '总错误数'
        },
        hints: {
          totalRequests: '所有模型累计请求数',
          totalTokens: '输入 + 输出 Token 总量',
          averageLatency: '按请求量加权的平均响应时间',
          totalErrors: '所有模型累计错误次数'
        },
        card: {
          requests: '{{value}} 请求',
          tokens: '{{value}} Token',
          errors: '{{value}} 错误'
        }
      },
      usage: {
        viewToggle: {
          list: '列表',
          card: '卡片'
        },
        filters: {
          model: '模型',
          allModels: '全部模型',
          loading: '加载中...',
          startTime: '开始时间',
          endTime: '结束时间'
        },
        metrics: {
          totalRequests: '总请求量',
          totalTokens: '总 Token',
          averageLatency: '平均延迟',
          totalErrors: '总错误'
        },
        table: {
          headers: {
            modelName: '模型名称',
            requests: '请求量',
            inputTokens: '输入 Token',
            outputTokens: '输出 Token',
            averageLatency: '平均延迟',
            errorRate: '错误率'
          }
        },
        detail: {
          drawerTitle: '请求明细',
          filters: {
            startTime: '开始时间',
            endTime: '结束时间'
          },
          table: {
            headers: {
              startedAt: '开始时间',
              requestId: '请求 ID',
              capability: '能力',
              attempts: '尝试数',
              inputTokens: '输入 Token',
              outputTokens: '输出 Token',
              latency: '总耗时',
              result: '结果'
            },
            status: {
              success: '成功',
              failure: '失败'
            }
          },
          empty: {
            title: '暂无请求明细',
            description: '该时间范围内没有找到请求记录。'
          }
        },
        empty: {
          title: '暂无用量数据',
          description: '当模型开始接收请求后，用量数据将出现在这里。'
        },
        error: '加载用量数据失败，请重试。',
        grid: {
          empty: {
            title: '暂无监控数据',
            description: '当模型开始接收请求后，监控数据将出现在这里。'
          },
          error: '加载监控数据失败。',
          requests: '{{value}} 请求',
          errors: '{{value}} 错误'
        }
      },
      errors: {
        filters: {
          model: '模型',
          allModels: '全部模型',
          loading: '加载中...',
          errorCode: '错误码',
          allErrorCodes: '全部错误码',
          startTime: '开始时间',
          endTime: '结束时间'
        },
        errorCodeLabels: {
          UPSTREAM_FAILURE: '上游调用失败',
          upstream_error: '上游错误',
          provider_timeout: '提供商超时',
          provider_rate_limited: '速率限制',
          provider_auth_failed: '鉴权失败',
          unsupported_capability: '不支持的能力',
          validation_error: '请求校验失败',
          session_closed: '会话已关闭'
        },
        table: {
          headers: {
            time: '时间',
            model: '模型',
            errorCode: '错误码',
            capability: '能力',
            errorMessage: '错误消息'
          },
          uncategorized: '未分类错误'
        },
        detail: {
          errorMessage: '错误消息',
          instance: '实例',
          capability: '能力',
          duration: '请求耗时'
        },
        empty: {
          title: '暂无错误记录',
          description: '没有找到符合条件的调用错误，这是一个好消息！'
        },
        error: '加载错误记录失败，请重试。'
      }
    } as const;
