// Auto-generated — do not edit manually
export const aiChat = {
      label: 'AI 对话',
      summary: '与 AI 模型或 Agent 进行实时对话。',
      trace: {
        title: '执行轨迹',
        description: '上下文、skills、工具与回复过程会按时间顺序显示。',
        expandButton: '展开执行轨迹',
        collapseButton: '收起执行轨迹',
        emptyTitle: '暂无可视化轨迹',
        emptyDescription: '发送一条 Agent 消息后，这里会展示运行过程与结果。',
        cardModeTitle: '当前为模型模式',
        cardModeDescription: '右侧轨迹区仅展示 Agent 的 tools、MCP、skills 调用过程。切换到 Agent 模式并发送消息后即可查看。',
        noTraceDescription: '选择一条含有轨迹的助手消息，或先发送一条 Agent 消息。',
        skillsLabel: '技能',
        reasonLabel: '原因',
        runDetails: '运行详情',
        toolExpand: '展开入参与输出',
        toolCollapse: '收起',
        skills: {
          applied: '{{count}} 个已应用',
          noSkills: '本次运行未注入 skills',
          noContext: '未发现 skills 上下文。'
        },
        tools: {
          callCount: '{{count}} 次调用结果',
          noCalls: '本次运行没有工具调用',
          noResults: '没有工具、MCP 或 delegate 调用结果。'
        },
        steps: {
          count: '{{count}} 个步骤'
        }
      },
      message: {
        assistant: 'AI 助手',
        sending: '发送中…',
        failed: '发送失败',
        viewTrace: '查看执行轨迹',
        viewedTrace: '已查看执行轨迹',
        viewTraceShort: '查看轨迹',
        viewedTraceShort: '已查看轨迹',
        newConversation: '开始一段新对话',
        startTyping: '在下方输入消息开始对话',
        copy: '复制',
        regenerate: '重新生成'
      },
      sessionList: {
        eyebrow: '会话',
        newChat: '新对话',
        defaultTitle: '新对话 {{time}}',
        count: '{{count}} 个对话',
        noMessages: '暂无消息',
        deleteConversation: '删除对话',
        empty: '暂无对话记录'
      },
      selector: {
        model: '模型',
        agent: 'Agent',
        noAvailableAgent: '无可用 Agent',
        noAvailableModel: '无可用模型'
      },
      input: {
        placeholder: '想聊点什么？直接输入，Enter 发送，Shift+Enter 换行',
        addAttachment: '新增附件能力',
        toolSettings: '工具设置',
        toolLabel: '工具',
        voiceInput: '语音输入',
        sendMessage: '发送消息',
        stopGeneration: '停止生成'
      },
      loading: '加载中...'
    } as const;
