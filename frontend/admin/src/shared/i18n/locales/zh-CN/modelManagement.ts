// Auto-generated — do not edit manually
export const modelManagement = {
      label: '模型管理',
      summary: '统一维护连接配置、模型卡、模型实例和模型绑定。',
      eyebrow: 'AI 模型中心',
      title: '模型管理',
      sections: {
        cards: '模型',
        instances: '部署实例',
        bindings: '场景绑定',
        profiles: '服务商连接',
        features: '能力定义'
      },
      detail: {
        fallbackTitle: '模型详情',
        backToList: '返回模型列表',
        sections: {
          overview: '基本信息',
          instances: '部署实例',
          bindings: '场景绑定'
        }
      },
      errors: {
        connectionProfileKeyMismatch: '连接标识不一致，请刷新后重试。',
        modelKeyMismatch: '模型标识不一致，请刷新后重试。',
        instanceKeyMismatch: '实例标识不一致，请刷新后重试。',
        bindingKeyMismatch: '绑定标识不一致，请刷新后重试。',
        unsupportedProvider: '不支持该服务商类型。',
        unsupportedScene: '不支持该业务场景。',
        invalidJsonKind: '格式不正确，请检查 JSON 格式。',
        invalidJson: 'JSON 格式有误，请修正后重试。',
        inUse: '该项正在被使用中，无法删除。',
        alreadyExists: '该标识已存在，请使用其他名称。',
        notFound: '未找到该项，可能已被删除。'
      },
      featureValidation: {
        booleanRequired: '请选择是或否。',
        integerRequired: '请输入整数。',
        numberRequired: '请输入数字。',
        enumRequired: '请选择一个有效选项。'
      },
      shared: {
        enabledStatusOptions: {
          all: '全部状态',
          enabledOnly: '仅启用',
          disabledOnly: '仅停用'
        },
        filterableOptions: {
          all: '全部筛选状态',
          filterableOnly: '仅可筛选',
          notFilterableOnly: '仅不可筛选'
        },
        routableOptions: {
          all: '全部路由状态',
          routableOnly: '仅可路由',
          notRoutableOnly: '仅不可路由'
        },
        healthStatusOptions: {
          all: '全部健康状态',
          healthyOnly: '仅健康',
          unhealthyOnly: '仅异常'
        }
      },
      models: {
        page: {
          newModel: '新建模型',
          viewModeTable: '列表',
          viewModeGrid: '卡片',
          filterFeature: '能力',
          filterFeatureAll: '全部',
          filterEnableStatus: '启用状态',
          emptyTitle: '暂无模型',
          createModel: '创建模型',
          deleteTitle: '删除模型',
          deleteDescription: '确认删除模型 {{name}} 吗？',
          confirmDelete: '确认删除',
          columns: {
            displayName: '显示名称',
            instances: '部署实例',
            bindings: '场景绑定',
            features: '能力',
            status: '状态',
            actions: '操作'
          },
          rowActions: {
            edit: '编辑',
            detail: '详情',
            test: '测试',
            testEmbedding: '向量测试',
            delete: '删除'
          },
          statsInstanceCount: '{{count}} 个实例',
          statsInstanceCountWithHealth: '{{count}} 个实例 · {{healthy}} 健康',
          statsBindingCount: '{{count}} 个绑定',
          noFeature: '未配置能力',
          status: {
            enabled: '启用',
            disabled: '停用'
          }
        },
        test: {
          title: '模型测试',
          empty: '输入消息开始测试，可连续对话。每轮回复下方会显示实例 / 首 Token 延迟 / 耗时 / token 等诊断信息。',
          inputPlaceholder: '输入测试消息...',
          send: '发送',
          stop: '停止',
          generating: '生成中...',
          diagnosis: {
            instanceKey: '实例',
            provider: 'Provider',
            ttft: '首 Token',
            total: '总耗时',
            inputTokens: '入',
            outputTokens: '出',
            finishReason: '结束',
            error: '错误',
            noData: '—'
          },
          errors: {
            noEnabledInstance: '该模型没有可用的启用实例',
            upstreamError: '上游调用失败'
          }
        },
        embeddingTest: {
          title: '向量模型测试 — {{model}}',
          empty: '输入文本，点击测试即可生成向量。下方会显示向量预览及诊断信息。',
          textLabel: '测试文本',
          textPlaceholder: '输入要向量化的文本...',
          dimensionsLabel: '向量维度（可选）',
          dimensionsPlaceholder: '默认',
          dimensionsHint: '留空使用模型默认维度。Embedding-3 支持 256~2048。',
          close: '关闭',
          test: '测试',
          testing: '测试中...',
          provider: 'Provider',
          model: '模型',
          dimensions: '维度',
          latency: '耗时',
          tokens: 'Tokens',
          vectorPreview: '向量预览',
          firstN: '前 {{n}} 位',
          unknownError: '未知错误'
        },
        drawer: {
          titleCreate: '新建模型',
          titleEdit: '编辑模型',
          navigateToDetail: '创建后跳转到详情页',
          fields: {
            modelKey: '模型标识',
            type: '类型',
            modelName: '模型名称',
            displayName: '显示名称',
            enableStatus: '启用状态',
            description: '描述',
            enabled: '启用',
            disabled: '停用',
            disabledBadge: ' (已禁用)',
            connectionProfileKey: '连接配置',
            connectionProfileLoading: '加载中...',
            connectionProfilePlaceholder: '请选择连接配置'
          },
          features: {
            sectionTitle: '可用能力',
            hint: '以下是系统中可用的能力定义。创建模型后，可在详情页中配置支持的能力。',
            loading: '加载中...',
            empty: '暂无能力定义，请先在「能力定义」页创建。'
          },
          pricing: {
            sectionTitle: '定价（每 1M tokens / USD）',
            inputPrice: '输入价格',
            outputPrice: '输出价格',
            cacheWritePrice: '缓存写入价格',
            cacheReadPrice: '缓存读取价格',
            unitHint: '$/MTok'
          },
          advanced: {
            sectionTitle: '高级配置',
            tags: '标签',
            tagsHint: '用于分类和搜索的标签。',
            routingPolicy: '路由策略',
            routingPolicyHint: '控制请求如何分配到不同实例。',
            retryPolicy: '重试策略',
            retryPolicyHint: '请求失败时的自动重试规则。'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建模型',
            save: '保存修改'
          },
          validation: {
            modelKeyRequired: '请输入模型标识。',
            modelNameRequired: '请输入模型名称。',
            displayNameRequired: '请输入显示名称。',
            connectionProfileKeyRequired: '请选择连接配置。'
          }
        },
        detail: {
          loading: '正在加载...',
          loadFailed: '加载失败，请稍后重试。',
          actions: {
            backToList: '返回列表',
            addInstance: '添加实例',
            addBinding: '添加绑定'
          },
          basicInfo: {
            cardTitle: '基本信息',
            cardDescription: '模型的基础配置信息。',
            modelLabel: '模型',
            modelKeyLabel: '模型标识',
            connectionProfileLabel: '连接配置',
            bindingsCount: '场景绑定',
            instancesCount: '部署实例',
            featureCount: '能力数',
            statusLabel: '状态',
            enabled: '已启用',
            disabled: '已停用',
            descriptionLabel: '描述',
            noDescription: '暂无描述',
            countUnit: '{{count}} 个'
          },
          instances: {
            cardTitle: '部署实例',
            cardDescription: '每个实例对应一个实际的模型部署，系统会根据优先级和权重自动选择最佳实例。',
            addButton: '新增实例',
            stats: {
              total: '总实例数',
              healthy: '健康比例',
              enabled: '已启用',
              regions: '区域数'
            },
            fields: {
              deployName: '部署名',
              connection: '连接',
              region: '区域',
              priority: '优先级',
              weight: '权重',
              timeout: '超时',
              type: '类型'
            },
            status: {
              enabled: '启用',
              disabled: '停用',
              healthy: '健康',
              unhealthy: '异常'
            },
            defaultDeploy: '默认部署',
            defaultRegion: '默认区域',
            editButton: '编辑',
            empty: '暂无部署实例'
          },
          bindings: {
            cardTitle: '场景绑定',
            cardDescription: '将此模型分配到不同的业务场景中。',
            addButton: '新增绑定',
            empty: '暂无场景绑定',
            status: {
              enabled: '启用',
              disabled: '停用'
            }
          }
        },
        featureSection: {
          cardTitle: '模型能力',
          configuredCount: '已配置 {{configured}} / {{total}} 项',
          configured: '已配置',
          unconfigured: '未配置',
          loading: '正在加载能力列表...',
          empty: '暂无可配置的能力',
          disabled: '已禁用',
          filterable: '可筛选',
          routable: '影响路由',
          save: '保存',
          saving: '保存中...',
          remove: '移除',
          removing: '删除中...',
          source: '数据来源',
          remark: '备注',
          noFeature: '未配置能力',
          dnd: {
            dragAriaLabel: '拖拽 {{name}}',
            removeAriaLabel: '移除 {{name}}',
            toggleAriaLabel: '切换 {{name}} 启用状态',
            addAriaLabel: '添加 {{name}}',
            edit: '编辑',
            valueNotSet: '(未设置)',
            valuePrefix: '值: ',
            add: '添加',
            remove: '移除',
            unconfiguredTitle: '可用能力',
            configuredTitle: '已配置能力',
            unconfiguredEmpty: '已添加所有能力',
            configuredEmpty: '从左侧拖拽能力到此处',
            hint: '提示：支持拖拽，也支持直接点击"添加 / 移除"完成配置。点击"编辑"可修改能力值。',
            editModal: {
              title: '编辑能力',
              enableLabel: '启用此能力',
              featureValue: '能力值',
              booleanTrue: '是',
              booleanFalse: '否',
              source: '数据来源',
              remark: '备注',
              cancel: '取消',
              save: '保存',
              saving: '保存中...'
            }
          }
        },
        tabs: {
          loading: '正在加载...',
          loadFailed: '加载失败，请稍后重试。',
          instances: {
            description: '每个实例对应一个实际的模型部署，系统会根据优先级和权重自动选择最佳实例。',
            addButton: '新增实例',
            stats: {
              total: '总实例数',
              healthy: '健康比例',
              enabled: '已启用',
              regions: '区域数'
            },
            fields: {
              deployName: '部署名',
              connection: '连接',
              region: '区域',
              priority: '优先级',
              weight: '权重',
              timeout: '超时',
              type: '类型'
            },
            status: {
              enabled: '启用',
              disabled: '停用',
              healthy: '健康',
              unhealthy: '异常'
            },
            defaultDeploy: '默认部署',
            defaultRegion: '默认区域',
            editButton: '编辑',
            empty: '暂无部署实例'
          },
          bindings: {
            description: '将此模型分配到不同的业务场景中。',
            addButton: '新增绑定',
            empty: '暂无场景绑定',
            status: {
              enabled: '启用',
              disabled: '停用'
            }
          },
          overview: {
            basicInfo: '基本信息',
            modelLabel: '模型',
            modelKeyLabel: '模型标识',
            bindingsCount: '场景绑定',
            instancesCount: '部署实例',
            featureCount: '能力数',
            statusLabel: '状态',
            enabled: '已启用',
            disabled: '已停用',
            descriptionLabel: '描述',
            noDescription: '暂无描述',
            countUnit: '{{count}} 个',
            status: {
              enabled: '启用',
              disabled: '停用'
            }
          }
        },
        deleteDialog: {
          title: '删除模型',
          description: '确认删除模型 {{name}} 吗？',
          confirmLabel: '确认删除'
        }
      },
      connectionProfiles: {
        page: {
          newProfile: '新建连接',
          columns: {
            profileKey: '连接名称',
            endpoint: '服务地址',
            status: '状态',
            actions: '操作'
          },
          filters: {
            provider: '服务商',
            allProviders: '全部服务商',
            enableStatus: '启用状态'
          },
          emptyTitle: '暂无服务商连接',
          status: {
            enabled: '启用',
            disabled: '停用'
          },
          rowActions: {
            edit: '编辑',
            delete: '删除'
          },
          deleteTitle: '删除连接',
          deleteDescription: '确认删除连接 {{name}} 吗？',
          confirmDelete: '确认删除'
        },
        drawer: {
          titleCreate: '新建服务商连接',
          titleEdit: '编辑服务商连接',
          description: '填写 AI 服务商的接入信息。高级参数可在底部展开配置。',
          fields: {
            profileKey: '连接标识',
            displayName: '显示名称',
            baseUrl: '服务地址',
            baseUrlHint: '填写 AI 服务商的 API 根地址。例如：OpenAI 填 https://api.openai.com/v1/，Azure OpenAI 填 https://{资源名}.openai.azure.com/openai/',
            wsUrl: 'WebSocket 地址',
            wsUrlHint: '用于实时语音等 WebSocket 场景。通常无需填写，仅在服务商提供独立 WebSocket 入口时配置。',
            apiVersion: 'API 版本',
            apiVersionHint: '部分服务商（如 Azure OpenAI）需要指定 API 版本号，例如 2025-04-01-preview。OpenAI 通常无需填写。',
            apiVersionPlaceholder: '如 2025-04-01-preview',
            enableConnection: '启用此连接',
            extraJson: '扩展参数',
            extraJsonHint: '服务商特有的额外配置项。'
          },
          advanced: {
            sectionTitle: '高级参数',
            collapse: '收起',
            expand: '展开'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建连接',
            save: '保存修改'
          },
          validation: {
            profileKeyRequired: '请输入连接标识。',
            displayNameRequired: '请输入显示名称。'
          }
        }
      },
      featureDefinitions: {
        page: {
          newFeature: '新建能力',
          columns: {
            featureKey: '能力名称',
            valueType: '数据类型',
            flags: '用途标记',
            status: '状态',
            actions: '操作'
          },
          filters: {
            valueType: '数据类型',
            allTypes: '全部类型',
            enableStatus: '启用状态',
            filterable: '可筛选',
            routable: '可路由'
          },
          flags: {
            filterable: '可筛选',
            routable: '影响路由'
          },
          status: {
            enabled: '启用',
            disabled: '停用'
          },
          rowActions: {
            edit: '编辑',
            delete: '删除'
          },
          emptyTitle: '暂无能力定义',
          deleteTitle: '删除能力',
          deleteDescription: '确认删除能力 {{name}} 吗？',
          confirmDelete: '确认删除',
          createNow: '立即创建'
        },
        drawer: {
          titleCreate: '新建能力定义',
          titleEdit: '编辑能力定义',
          description: '定义模型可以声明的能力标签，用于筛选和路由。',
          fields: {
            featureKey: '能力标识',
            displayName: '显示名称',
            valueType: '数据类型',
            description: '描述',
            allowedValues: '允许的选项',
            allowedValuesHint: '仅在数据类型为枚举时使用，定义可选值列表。',
            isFilterable: '支持筛选',
            isRoutable: '影响路由',
            isEnabled: '启用'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建能力',
            save: '保存修改'
          },
          validation: {
            featureKeyRequired: '请输入能力标识。',
            displayNameRequired: '请输入显示名称。',
            valueTypeRequired: '请选择数据类型。'
          }
        }
      },
      modelBindings: {
        page: {
          newBinding: '新建绑定',
          columns: {
            bindingKey: '绑定名称',
            usage: '用途',
            mapping: '能力 / 模型',
            status: '状态',
            actions: '操作'
          },
          filters: {
            capability: '能力',
            allCapabilities: '全部能力',
            modelKey: '关联模型',
            enableStatus: '启用状态'
          },
          status: {
            enabled: '启用',
            disabled: '停用'
          },
          rowActions: {
            edit: '编辑',
            delete: '删除'
          },
          emptyTitle: '暂无场景绑定',
          createBinding: '创建绑定',
          deleteTitle: '删除绑定',
          deleteDescription: '确认删除绑定 {{name}} 吗？',
          confirmDelete: '确认删除'
        },
        drawer: {
          titleCreate: '新建绑定',
          titleEdit: '编辑绑定',
          description: '将模型分配到业务场景中。',
          fields: {
            bindingKey: '绑定标识',
            displayName: '显示名称',
            preset: '用途模板',
            presetHint: '选择后自动填入能力类型，也可在下方手动调整。',
            capability: '能力',
            modelKey: '关联模型',
            modelKeyLoading: '加载中...',
            modelKeyPlaceholder: '请选择模型',
            enableBinding: '启用此绑定',
            metadataJson: '扩展参数',
            metadataJsonHint: '场景相关的额外配置项。'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建绑定',
            save: '保存修改'
          },
          validation: {
            bindingKeyRequired: '请输入绑定标识。',
            displayNameRequired: '请输入显示名称。',
            modelKeyRequired: '请选择关联模型。'
          }
        }
      },
      modelInstances: {
        page: {
          newInstance: '新建实例',
          columns: {
            instanceKey: '实例',
            modelName: '模型名称',
            connectionProfileKey: '服务商连接',
            priority: '优先级 / 权重 / 超时',
            status: '状态',
            actions: '操作'
          },
          filters: {
            modelKey: '所属模型',
            connectionProfileKey: '服务商连接',
            feature: '能力',
            featureAll: '全部',
            featureSupport: '能力支持',
            featureSupportAll: '全部',
            featureSupportTrue: '支持',
            featureSupportFalse: '不支持',
            featureValue: '能力值',
            type: '类型',
            typeAll: '全部类型',
            loading: '加载中...',
            enableStatus: '启用状态',
            healthStatus: '健康状态'
          },
          metrics: {
            total: '总数',
            totalHint: '符合筛选条件的实例总数',
            enabled: '已启用',
            enabledHint: '当前页已启用的实例数',
            healthy: '运行正常',
            healthyHint: '当前页运行正常的实例数',
            typeCount: '能力类型',
            typeCountHint: '当前页涉及的能力类型数'
          },
          status: {
            enabled: '启用',
            disabled: '停用',
            healthy: '健康',
            unhealthy: '异常'
          },
          rowActions: {
            edit: '编辑',
            delete: '删除'
          },
          emptyTitle: '暂无部署实例',
          createInstance: '创建实例',
          deleteTitle: '删除实例',
          deleteDescription: '确认删除模型实例 {{name}} 吗？',
          confirmDelete: '确认删除'
        },
        drawer: {
          titleCreate: '新建实例',
          titleEdit: '编辑实例',
          description: '实例代表一个实际的模型部署。能力配置继承自所属模型，连接配置在实例级单独选择。',
          fields: {
            modelKey: '所属模型',
            modelKeyLoading: '加载中...',
            modelKeyPlaceholder: '请选择模型',
            instanceKey: '实例标识',
            connectionProfileKey: '所用连接',
            connectionProfileLoading: '加载中...',
            connectionProfilePlaceholder: '请选择服务商连接',
            deploymentName: '部署名称',
            region: '区域',
            priority: '优先级',
            weight: '权重',
            timeout: '默认超时 (ms)',
            apiKey: 'API 密钥',
            apiKeyHintEdit: '留空表示不修改当前密钥。',
            apiKeyHintCreate: '提交后不再显示，请妥善保管。',
            apiKeyPlaceholderEdit: '留空不修改',
            instanceUrl: '实例 URL',
            instanceUrlHint: '由所用连接自动决定，不可手动编辑。',
            isEnabled: '启用实例',
            isHealthy: '健康状态',
            extraJson: '扩展参数',
            extraJsonHint: '实例的额外配置项。',
            advancedOptions: '高级选项'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建实例',
            save: '保存修改'
          },
          validation: {
            modelKeyRequired: '请选择所属模型。',
            instanceKeyRequired: '请输入实例标识。',
            connectionProfileKeyRequired: '请选择所用连接。',
            priorityMin: '优先级不能小于 0。',
            weightMin: '权重必须大于 0。',
            timeoutMin: '默认超时必须大于 0。',
            apiKeyRequired: '请输入实例密钥。'
          }
        }
      },
      instancesByModel: {
        modelList: '模型列表',
        noModels: '暂无模型',
        selectModel: '请选择模型',
        selectModelHint: '从左侧模型列表中选择一个模型，查看其部署实例',
        instancesTitle: '{{count}} 个部署实例',
        noInstances: '暂无部署实例',
        emptyTitle: '该模型暂无部署实例',
        emptyDescription: '点击右上角按钮为该模型创建第一个实例。',
        instanceCount: '{{count}} 个实例'
      }
    } as const;
