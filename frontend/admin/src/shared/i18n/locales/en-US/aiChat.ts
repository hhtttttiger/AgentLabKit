// Auto-generated — do not edit manually
export const aiChat = {
  label: 'AI chat',
  summary: 'Chat with AI models or agents in real time.',
  trace: {
    title: 'Execution trace',
    description: 'Context, skills, tool calls, and reply steps are shown in chronological order.',
    expandButton: 'Expand trace',
    collapseButton: 'Collapse trace',
    emptyTitle: 'No trace available',
    emptyDescription: 'Send an agent message and the execution trace will appear here.',
    cardModeTitle: 'Model mode',
    cardModeDescription: 'The trace panel only shows Agent tool / MCP / skill calls. Switch to Agent mode and send a message to see traces.',
    noTraceDescription: 'Select an assistant message with a trace, or send an Agent message first.',
    skillsLabel: 'Skills',
    reasonLabel: 'Reason',
    runDetails: 'Run details',
    toolExpand: 'Show arguments and output',
    toolCollapse: 'Collapse',
    skills: {
      applied: '{{count}} applied',
      noSkills: 'No skills injected this run',
      noContext: 'No skills context found.'
    },
    tools: {
      callCount: '{{count}} call results',
      noCalls: 'No tool calls this run',
      noResults: 'No tool, MCP, or delegate call results.'
    },
    steps: {
      count: '{{count}} steps'
    }
  },
  message: {
    assistant: 'AI assistant',
    sending: 'Sending…',
    failed: 'Send failed',
    viewTrace: 'View execution trace',
    viewedTrace: 'Viewing execution trace',
    viewTraceShort: 'View trace',
    viewedTraceShort: 'Viewed trace',
    newConversation: 'Start a new conversation',
    startTyping: 'Type a message below to start the conversation',
    copy: 'Copy',
    regenerate: 'Regenerate'
  },
  sessionList: {
    eyebrow: 'Sessions',
    newChat: 'New chat',
    defaultTitle: 'New chat {{time}}',
    count: '{{count}} conversations',
    noMessages: 'No messages yet',
    deleteConversation: 'Delete conversation',
    empty: 'No conversations yet'
  },
  selector: {
    model: 'Model',
    agent: 'Agent',
    noAvailableAgent: 'No available Agent',
    noAvailableModel: 'No available model'
  },
  input: {
    placeholder: 'What would you like to talk about? Type here, press Enter to send, Shift+Enter for a new line',
    addAttachment: 'Add attachment capability',
    toolSettings: 'Tool settings',
    toolLabel: 'Tools',
    voiceInput: 'Voice input',
    sendMessage: 'Send message',
    stopGeneration: 'Stop generation'
  },
  inspector: {
    tabs: {
      run: 'Run',
      trace: 'Trace',
      tools: 'Tools',
      context: 'Context',
      cost: 'Cost',
      eval: 'Eval',
    },
    notAvailable: {
      run: 'Run details not available for this session',
      tools: 'Tool details not available for this session',
      context: 'Context details not available for this session',
      cost: 'Cost details not available for this session',
      eval: 'Evaluation not available for this session',
    },
    noRunId: 'No run ID available. Send a message to create a run.',
    runAvailable: 'Run created successfully',
    openRunDetail: 'Open Run Detail',
  },
  loading: 'Loading...'
} as const;
