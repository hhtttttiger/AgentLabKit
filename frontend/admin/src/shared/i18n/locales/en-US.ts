// Auto-generated from resources.ts — do not edit manually
export const common = {
  userMenu: {
    ariaLabel: 'User menu',
    account: 'Account',
    language: 'Language',
    languageTitle: 'Choose language',
    preferences: 'Preferences',
    preferencesTitle: 'Preferences',
    back: 'Back',
    localeShort: {
      'zh-CN': '中文',
      'en-US': 'EN'
    },
    logout: 'Log out'
  },
  preferences: {
    theme: {
      dark: 'Dark mode',
      light: 'Light mode'
    },
    motion: {
      enable: 'Enable motion',
      disable: 'Disable motion'
    },
    accent: 'Accent color',
    accentOptions: {
      blue: 'Blue (default)',
      violet: 'Violet',
      emerald: 'Emerald',
      rose: 'Rose',
      amber: 'Amber',
      orange: 'Orange'
    },
    zoom: 'Zoom',
    language: {
      label: 'Display language',
      options: {
        'zh-CN': '简体中文',
        'en-US': 'English'
      }
    },
    catalog: {
      scenes: {
        gateway: 'Gateway',
        voice: 'Voice',
      },
      capabilities: {
        Text: 'Text Chat',
        Multimodal: 'Multimodal',
        Embedding: 'Embedding',
        SpeechBatch: 'Speech Batch',
        SpeechStream: 'Speech Stream',
        Realtime: 'Realtime',
        Image: 'Image Generation',
        Tool: 'Tool Calling',
      },
      bindingPresets: {
        custom: 'Custom',
        gateway_text: { label: 'Chat / Q&A', description: 'General text chat, Q&A, summarization and rewriting.' },
        gateway_multimodal: { label: 'Multimodal chat', description: 'Chat and understanding with mixed text + image input.' },
        gateway_embedding: { label: 'Embeddings', description: 'Text vectorization for retrieval, similarity and RAG.' },
        gateway_speech_batch: { label: 'Transcription (batch)', description: 'Batch audio-to-text for offline recording files.' },
        gateway_speech_stream: { label: 'Transcription (stream)', description: 'Real-time streaming audio-to-text while recording.' },
        gateway_image: { label: 'Image generation', description: 'Generate images from text descriptions.' },
        gateway_realtime: { label: 'Realtime multimodal', description: 'Low-latency realtime voice/video conversation.' },
        gateway_tool: { label: 'Tool calling', description: 'Model can call external tools/functions (agent scenarios).' },
        voice_text: { label: 'Voice assistant text', description: 'Text chat model used by the voice assistant backend.' },
        voice_realtime: { label: 'Voice realtime channel', description: 'Realtime voice conversation channel for the voice assistant.' },
      },
    },
  },
  login: {
    title: 'AI Admin',
    username: 'Username',
    usernamePlaceholder: 'Enter username',
    password: 'Password',
    passwordPlaceholder: 'Enter password',
    submit: 'Log in',
    submitting: 'Signing in…',
    errorFallback: 'Sign-in failed. Check your username and password.',
    preferences: {
      ariaLabel: 'Login preferences',
      trigger: 'Interface',
      helper: 'Language, accent, and theme',
      panelLabel: 'Login preference controls',
      openPanel: 'Open login preferences. Current: {{locale}}, {{accent}}, {{theme}}',
      closePanel: 'Close login preferences. Current: {{locale}}, {{accent}}, {{theme}}',
      language: 'Language',
      accent: 'Accent',
      theme: 'Theme'
    }
  },
  themeToggle: {
    toLight: 'Switch to light mode',
    toDark: 'Switch to dark mode'
  },
  nav: {
    ariaLabel: 'Modules',
    brandTitle: 'AI Admin',
    brandSubtitle: 'Frontend Base',
    aiChat: 'AI chat',
    agentManagement: 'Agent management',
    modelManagement: 'Model management',
    glossary: 'Glossary',
    knowledgeBase: 'Knowledge base',
    modelMonitoring: 'Model monitoring',
    costAnalysis: 'Cost analysis',
    observability: 'Observability',
    memory: 'Memory',
    evaluation: 'Evaluation',
    voiceLab: 'Voice latency debug',
    collapse: 'Collapse menu',
    expand: 'Expand menu',
    collapseShort: 'Collapse',
    expandShort: 'Expand'
  },
  actions: {
    create: 'Create',
    edit: 'Edit',
    refresh: 'Refresh',
    reset: 'Reset',
    delete: 'Delete',
    cancel: 'Cancel',
    backToList: 'Back to list',
    addInstance: 'Add instance',
    addBinding: 'Add binding'
  },
  pagination: {
    totalPrefix: '',
    totalSuffix: ' total',
    pageSizeOption: '{{count}} / page',
    previousPage: 'Previous page',
    nextPage: 'Next page',
    jumpTo: 'Go to',
    pageUnit: 'page'
  },
  datePicker: {
    selectDate: 'Select date',
    previousMonth: 'Previous month',
    nextMonth: 'Next month',
    clear: 'Clear'
  },
  states: {
    loading: 'Loading',
    loadingFailed: 'Load failed',
    empty: 'No data',
    unknown: 'Unknown',
    processing: 'Processing...',
    lastUpdated: 'Last updated {{value}}'
  },
  api: {
    requestFailed: 'Request failed.',
    sessionExpired: 'Session expired. Please log in again.'
  },
  toast: {
    created: 'Created successfully',
    updated: 'Updated successfully',
    deleted: 'Deleted successfully',
    saved: 'Saved successfully',
    operationSuccess: 'Operation successful',
    operationFailed: 'Operation failed',
    syncCompleted: 'Sync completed',
    syncFailed: 'Sync failed',
    importCompleted: 'Import completed',
    importFailed: 'Import failed',
    exportCompleted: 'Export completed',
    uploadSuccess: 'Uploaded successfully',
    uploadFailed: 'Upload failed',
    reindexSubmitted: 'Re-index submitted',
    consolidateDone: 'Memories consolidated',
    deactivateDone: 'Deactivated',
    published: 'Published successfully',
    unpublished: 'Unpublished'
  },
  dialogs: {
    confirm: {
      dangerBody: 'This action cannot be undone. Make sure no other configuration depends on this resource.',
      defaultBody: 'Please confirm this action.'
    }
  },
  modules: {
    aiChat: {
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
      loading: 'Loading...'
    },
    agentManagement: {
      label: 'Agent management',
      summary: 'Manage agent definitions, releases, and execution audits.',
      eyebrow: 'AI Agent Center',
      title: 'Agent management',
      sections: {
        agents: 'Agents',
        mcpServers: 'MCP Servers',
        skills: 'Skills',
        tools: 'Tools'
      },
      status: {
        allStatuses: 'All statuses',
        draft: 'Draft',
        published: 'Published',
        disabled: 'Disabled',
        archived: 'Archived',
        active: 'Active',
        deprecated: 'Deprecated',
        success: 'Success',
        failed: 'Failed',
        timeout: 'Timeout',
        enabled: 'Enabled',
        stopped: 'Stopped'
      },
      common: {
        cancel: 'Cancel',
        save: 'Save',
        submitting: 'Submitting...',
        loading: 'Loading',
        close: 'Close',
        expand: 'Expand',
        collapse: 'Collapse',
        createNow: 'Create now'
      },
      agents: {
        page: {
          newAgent: 'New agent',
          ownerTeamLabel: 'Owning team',
          ownerTeamPlaceholder: 'Search teams',
          emptyTitle: 'No agents'
        },
        columns: {
          status: 'Status',
          publishedVersion: 'Published version',
          ownerTeam: 'Owning team',
          createdAt: 'Created',
          actions: 'Actions'
        },
        actions: {
          manageVersions: 'Manage prompts & versions',
          editDefinition: 'Edit definition'
        },
        drawer: {
          titleCreate: 'New agent',
          titleEdit: 'Edit definition',
          descCreate: 'Create the agent definition first, then use versions to configure its prompt, model and run strategy.',
          descEdit: 'Only update name, description, ownership, tags and metadata here. Edit prompts, model and run config in versions.',
          agentKey: 'Agent ID',
          agentKeyPlaceholder: 'e.g. sales-assistant',
          agentKeyRequired: 'Agent ID is required.',
          displayName: 'Display name',
          displayNameRequired: 'Display name is required.',
          ownerTeam: 'Owning team',
          description: 'Description',
          descriptionPlaceholder: 'Describe this agent\'s responsibility and business purpose',
          buttonCreate: 'Create agent',
          buttonEdit: 'Save definition',
          advanced: 'Advanced definition',
          tags: 'Tags',
          tagsHint: 'String array for search, filtering and classification.',
          metadata: 'Metadata',
          metadataHint: 'For extended business metadata only; does not affect prompt or runtime behavior.'
        },
        detail: {
          eyebrow: 'Agent details',
          ariaLabel: 'Agent detail workspace',
          backTitle: 'Back to list',
          breadcrumb: 'Agent management',
          tabVersions: 'Versions',
          tabAudits: 'Execution audits',
          createVersion: 'New version',
          disable: 'Disable',
          publishedVersion: 'Published version',
          notPublished: 'Not published',
          ownerTeam: 'Owning team',
          notSet: 'Not set',
          createdAt: 'Created',
          agentNotFound: 'Agent not found.',
          confirmPublish: {
            title: 'Publish version',
            description: 'Confirm publishing version v{{versionNumber}} as the active version?',
            label: 'Confirm publish',
            body: 'After publishing, this version becomes the default runtime version. The current published version will be archived.'
          },
          confirmDisable: {
            title: 'Disable agent',
            description: 'Confirm disabling {{name}}?',
            label: 'Confirm disable',
            body: 'After disabling, the runtime will reject new execution requests for this agent. In-flight requests are not affected.'
          }
        }
      },
      audits: {
        actions: {
          viewTrace: 'View trace',
          copyRunId: 'Copy full Run ID'
        },
        actionLabels: {
          reply: 'Reply',
          handoff: 'Handoff',
          error: 'Error'
        },
        statusLabels: {
          success: 'Success',
          failed: 'Failed',
          timeout: 'Timeout'
        },
        filterStatuses: {
          all: 'All statuses',
          success: 'Success',
          error: 'Failed',
          timeout: 'Timeout'
        },
        columns: {
          version: 'Version',
          status: 'Status',
          action: 'Action',
          replyPreview: 'Reply preview',
          startedAt: 'Started',
          completedAt: 'Completed',
          details: 'Details'
        },
        panel: {
          title: 'Execution audits',
          description: 'View run records and trace details for all versions of this agent.'
        },
        searchPlaceholder: 'Search Run ID…',
        loadError: 'Failed to load audit records.',
        emptyFiltered: {
          title: 'No matching records',
          description: 'Try modifying search terms or clearing filters.',
          clearFilters: 'Clear filters'
        },
        emptyAll: {
          title: 'No execution records'
        },
        detail: {
          title: 'Execution details',
          description: 'View the full context, skills, tool calls and reply trace for one agent run.',
          loadError: 'Failed to load execution details.',
          loadingTitle: 'Loading',
          loadingDescription: 'Reading detailed trace for this run.',
          emptyTitle: 'No execution details',
          emptyDescription: 'This audit record has no trace information to display.'
        }
      },
      mcpServers: {
        allTransportTypes: 'All transport types',
        columns: {
          name: 'Name',
          transport: 'Transport',
          endpoint: 'Connection info',
          tags: 'Tags',
          status: 'Status',
          createdAt: 'Created',
          actions: 'Actions'
        },
        statusEnabled: 'Enabled',
        statusStopped: 'Disabled',
        actions: {
          edit: 'Edit',
          delete: 'Delete'
        },
        newServer: 'New MCP server',
        filterTransport: 'Transport',
        searchLabel: 'Search',
        searchPlaceholder: 'Name, command, URL, tags',
        emptyTitle: 'No MCP server configurations',
        confirmDelete: {
          title: 'Delete MCP server',
          description: 'Confirm deleting MCP server "{{name}}"?',
          label: 'Delete'
        },
        drawer: {
          titleCreate: 'New MCP server',
          titleEdit: 'Edit MCP server',
          description: 'Configure the transport and connection parameters for the MCP server.',
          nameLabel: 'Name',
          namePlaceholder: 'e.g. filesystem',
          nameRequired: 'Name is required.',
          transportLabel: 'Transport type',
          stdioCommandRequired: 'Command is required for stdio transport.',
          httpUrlRequired: 'URL is required for http/sse transport.',
          toolNamePrefix: 'Tool name prefix',
          tagsLabel: 'Tags',
          tagsPlaceholder: 'e.g. prod, stable (comma-separated)',
          tagsHint: 'Written to config.tags.',
          fullConfig: 'Full config',
          configHint: 'Merged with command/url, prefix and tags before submission.',
          enabledLabel: 'Enabled',
          buttonCreate: 'Create',
          buttonEdit: 'Save changes',
          loadingDetail: 'Loading MCP server details...',
          commandPlaceholder: 'e.g. npx',
          urlPlaceholder: 'e.g. http://localhost:3000/mcp',
          toolNamePrefixPlaceholder: 'Optional, e.g. fs_'
        }
      },
      skills: {
        allStatuses: 'All statuses',
        columns: {
          skillKey: 'Skill ID',
          status: 'Status',
          version: 'Version',
          tags: 'Tags',
          updatedAt: 'Updated',
          actions: 'Actions'
        },
        statusPublished: 'Published',
        statusDraft: 'Draft',
        actions: {
          edit: 'Edit',
          workbench: 'Orchestration workbench',
          publish: 'Publish',
          delete: 'Delete'
        },
        newSkill: 'New skill',
        filterStatus: 'Status',
        filterTag: 'Tags',
        filterTagPlaceholder: 'Filter by tag',
        filterSearch: 'Search',
        filterSearchPlaceholder: 'Name, ID, version',
        emptyTitle: 'No skills',
        emptyDescription: 'Create a skill to configure prompt sections, tool bindings and the orchestration workbench.',
        confirmDelete: {
          title: 'Delete skill',
          description: 'Confirm deleting skill "{{name}}"?',
          label: 'Confirm delete'
        },
        drawer: {
          titleCreate: 'New skill',
          titleEdit: 'Edit skill',
          description: 'Define a reusable skill; the form maps to the backend Skill Spec.',
          skillKeyLabel: 'Skill ID',
          skillKeyPlaceholder: 'e.g. summarize-document',
          skillKeyRequired: 'Skill ID is required.',
          skillKeyPattern: 'Skill ID must start with a lowercase letter and contain only lowercase letters, digits, dots, hyphens and underscores.',
          displayNameLabel: 'Display name',
          displayNameRequired: 'Display name is required.',
          versionLabel: 'Version',
          versionPlaceholder: 'e.g. 1.0.0',
          versionRequired: 'Version is required.',
          descriptionLabel: 'Description',
          tagsLabel: 'Tags',
          tagsPlaceholder: 'Comma-separated, e.g. nlp, summarization',
          buttonCreate: 'Create skill',
          buttonEdit: 'Save changes',
          loadingDetail: 'Loading...',
          promptSectionsTitle: 'Prompt Sections',
          addPromptSection: 'Add prompt section',
          emptyPromptSections: 'No prompt sections added yet.',
          promptSectionTitle: 'Section #{{number}}',
          promptSectionKeyRequired: 'Prompt Section #{{number}} key is required.',
          promptSectionContentRequired: 'Prompt Section #{{number}} content is required.',
          toolBindingsTitle: 'Tool bindings',
          addTool: 'Add tool',
          emptyToolBindings: 'No tool bindings added yet.',
          toolTitle: 'Tool #{{number}}',
          toolNameRequired: 'Tool #{{number}} name is required.',
          advancedConfig: 'Advanced config',
          invocationModeAuto: 'Auto (LLM decides)',
          invocationModeManual: 'Manual only',
          invocationModeDisabled: 'Disabled',
          toolNameLabel: 'Tool name',
          invocationModeLabel: 'Invocation mode',
          requiredLabel: 'Required',
          enabledLabel: 'Enabled',
          sectionKeyPlaceholder: 'e.g. system / context',
          sectionSortOrder: 'Sort order',
          sectionContent: 'Content',
          configSchemaLabel: 'Config schema (spec.configSchema)'
        },
        workbench: {
          title: 'Skill orchestration workbench',
          eyebrow: 'Skill orchestration',
          pageTitle: '{{name}} orchestration workbench',
          backToList: 'Back to skills',
          autoLayout: 'Auto layout',
          saveOrchestration: 'Save orchestration',
          skillKeyLabel: 'Skill ID:',
          validationValid: 'Structure valid',
          validationInvalid: 'Validation issues',
          unsavedChanges: 'Unsaved changes',
          synced: 'In sync with loaded version',
          versionLabel: 'Version:',
          outlinePanel: 'Steps',
          inspectorPanel: 'Node inspector',
          canvasPanel: 'Flow canvas',
          validationPanel: 'Validation',
          remoteUpdateMessage: 'Remote skill definition updated; your local draft is preserved.',
          applyRemoteVersion: 'Load latest remote version',
          loadingMessage: 'Loading skill orchestration workbench…',
          skillNotFound: 'Skill not found.',
          nodeLabels: {
            start: 'Start',
            task: 'Task',
            decision: 'Decision',
            handoff: 'Handoff',
            terminal: 'Terminal'
          },
          edgeTypes: {
            default: 'Default',
            condition: 'Condition',
            fallback: 'Fallback',
            error: 'Error',
            handoff: 'Handoff'
          },
          validation: {
            pass: 'Validation passed',
            fail: 'Validation failed',
            errorCount: '{{errors}} errors, {{warnings}} warnings',
            errorsSection: 'Errors',
            warningsSection: 'Warnings'
          },
          defaults: {
            taskTitle: 'New step',
            handoffTitle: 'Hand off to agent',
            handoffSummary: 'Summarize the current context and transfer to a human agent.',
            terminalTitle: 'Done',
            terminalNote: 'Flow complete.',
            decisionTitle: 'Routing decision',
            decisionQuestion: 'Select the next branch based on current information.',
            enterDecisionLabel: 'Enter decision',
            continueAutoLabel: 'Continue auto',
            continueAutoDescription: 'Continue when auto-processing conditions are met',
            handoffBranchLabel: 'Hand off',
            branchHandoffLabel: 'Handoff',
            branchTerminalLabel: 'End flow',
            branchConditionDescription: 'End flow when branch {{n}} matches',
            taskBranchHandoff: 'Handoff',
            taskBranchFallbackHandoff: 'Fallback handoff',
            taskBranchFallbackTerminal: 'Fallback end',
            taskBranchErrorHandoff: 'Error handoff',
            taskBranchErrorTerminal: 'Error end',
            fallbackNote: 'Route to fallback on failure.',
            toolReason: 'Use {{toolId}} to support the "{{title}}" step.'
          },
          inspector: {
            noSelectionTitle: 'No node selected',
            noSelectionDescription: 'Select a node or transition from the outline or canvas to edit it here.',
            startNodeTitle: 'Start node',
            startNodeDescription: 'The start node defines the entry point. Configure subsequent steps on other nodes.',
            deleteTask: 'Delete task node',
            deleteHandoff: 'Delete handoff node',
            deleteTerminal: 'Delete terminal node',
            taskTitle: 'Step title',
            taskGoal: 'Step goal',
            taskInherited: 'Inherited inputs',
            taskRequired: 'Required inputs',
            taskOptional: 'Optional inputs',
            taskOutput: 'Output',
            fallbackPolicyLabel: 'Fallback policy',
            fallbackStay: 'Stay on current step',
            fallbackHandoffOption: 'Hand off',
            fallbackGoto: 'Go to fallback branch',
            fallbackTargetLabel: 'Fallback target',
            fallbackTargetPlaceholder: 'Select a transition',
            fallbackTargetDisabled: 'Not applicable in this mode',
            fallbackNoteLabel: 'Fallback note',
            branchSectionTitle: 'Error & handoff branches',
            branchSectionDescription: 'Add fallback, error, and human handoff flows for the current task.',
            addFallbackBranch: 'Add fallback branch',
            addErrorBranch: 'Add error branch',
            addHandoffBranch: 'Add handoff branch',
            noBranches: 'No extra branches configured yet.',
            targetNode: 'Target: {{title}}',
            branchLabelFallback: 'Fallback',
            branchLabelError: 'Error',
            branchLabelHandoff: 'Handoff',
            toolSectionTitle: 'Tool plan',
            toolSectionDescription: 'Manage the skill tools to invoke for this step.',
            addToolButton: 'Add tool',
            noTools: 'No tools configured yet.',
            removeTool: 'Remove',
            noAvailableTools: 'All enabled tools have been added.',
            requiredBadge: 'Required',
            noDescription: 'No description.',
            toolDetailTitle: 'Tool details: {{name}}',
            toolNotFound: 'This tool is no longer in the tool library.',
            toolCallReason: 'Call reason',
            addToolById: 'Add {{id}}',
            handoffTitle: 'Handoff title',
            handoffTypeLabel: 'Handoff type',
            handoffTypeHuman: 'Human agent',
            handoffTypeTicket: 'Create ticket',
            handoffTypeOtherAgent: 'Transfer to other Agent',
            handoffSummaryLabel: 'Handover summary template',
            terminalTitle: 'Terminal title',
            terminalOutcomeLabel: 'Outcome',
            terminalResolved: 'Resolved',
            terminalBlocked: 'Blocked',
            terminalCancelled: 'Cancelled',
            terminalNoteLabel: 'Resolution note',
            decisionTitle: 'Decision title',
            decisionQuestion: 'Decision question',
            decisionBranchSectionTitle: 'Branch overview',
            decisionBranchSectionDescription: 'Add new terminal or handoff transitions to this decision node.',
            addConditionBranch: 'Add condition branch',
            addDecisionHandoffBranch: 'Add handoff branch',
            transitionKindHandoff: 'Handoff',
            transitionKindCondition: 'Condition',
            transitionKindPriority: '{{kind}} / priority {{priority}}',
            transitionName: 'Transition name',
            transitionType: 'Transition type',
            transitionPriorityLabel: 'Priority',
            transitionCondition: 'Condition description',
            transitionField: 'Condition field',
            transitionOperator: 'Operator',
            transitionValue: 'Match value',
            operatorEq: 'Equals',
            operatorIn: 'In'
          },
          outline: {
            insertBefore: 'Insert task step before',
            insertAfter: 'Insert task step after',
            insertDecisionAfter: 'Insert decision step after'
          }
        }
      },
      tools: {
        allTypes: 'All types',
        allStatuses: 'All statuses',
        statusActive: 'Active',
        statusDeprecated: 'Deprecated',
        statusDisabled: 'Disabled',
        columns: {
          toolName: 'Tool name',
          type: 'Type',
          status: 'Status',
          tags: 'Tags',
          timeout: 'Timeout',
          updatedAt: 'Updated'
        },
        actions: {
          view: 'View',
          edit: 'Edit',
          disable: 'Disable'
        },
        confirmDisable: 'Confirm disabling tool "{{name}}"?',
        syncResult: 'Sync complete — {{count}} tools synced.',
        refreshButton: 'Refresh',
        syncButton: 'Sync built-in tools',
        newToolButton: 'New external tool',
        filterType: 'Type',
        filterStatus: 'Status',
        filterSearch: 'Search',
        filterSearchPlaceholder: 'Tool name or description',
        loadError: 'Failed to load tool list. Please refresh.',
        loadingText: 'Loading…',
        emptyTitle: 'No tools',
        emptyDescription: 'No matching tool definitions.',
        drawer: {
          titleBuiltin: 'View built-in tool: {{name}}',
          titleEdit: 'Edit external tool: {{name}}',
          titleCreate: 'New external tool',
          builtinNotice: 'Built-in tools are managed by the Python runtime and synced automatically on startup. View only.',
          toolNameLabel: 'Tool name',
          toolNameRequired: 'Tool name is required.',
          toolNamePattern: 'Tool name must start with a lowercase letter and contain only lowercase letters, digits and underscores.',
          toolNameSnakeCase: 'Tool name (snake_case)',
          displayNameLabel: 'Display name',
          displayNameRequired: 'Display name is required.',
          descriptionLabel: 'Description',
          descriptionRequired: 'Description is required.',
          descriptionLlm: 'Description (LLM function-calling)',
          endpointLabel: 'Endpoint URL',
          endpointRequired: 'Endpoint URL is required.',
          timeoutLabel: 'Timeout (seconds)',
          maxRetriesLabel: 'Max retries',
          tagsLabel: 'Tags (comma-separated)',
          parametersSchemaLabel: 'Parameters schema (JSON Schema)',
          saveButton: 'Save',
          savingButton: 'Saving…'
        }
      },
      versions: {
        statusDraft: 'Draft',
        statusPublished: 'Published',
        statusArchived: 'Archived',
        columns: {
          versionNumber: 'Version',
          status: 'Status',
          label: 'Label',
          changelog: 'Changelog',
          model: 'Model',
          publishedAt: 'Published',
          createdAt: 'Created',
          actions: 'Actions'
        },
        actions: {
          view: 'View',
          createDraft: 'Create draft',
          editDraft: 'Edit draft',
          publish: 'Publish'
        },
        searchPlaceholder: 'Search version / label / changelog…',
        allStatuses: 'All statuses',
        publishedReadonlyInfo: 'Published versions are read-only. To change prompt, model or run strategy, create a draft from a version and publish it.',
        loadError: 'Failed to load version list.',
        emptyFiltered: {
          title: 'No matching versions',
          description: 'Try modifying search terms or clearing filters.',
          clearFilters: 'Clear filters'
        },
        emptyAll: {
          title: 'No versions yet',
          description: 'Create the first version to configure prompt, model and run strategy for this agent.',
          createFirst: 'Create first version'
        },
        drawer: {
          titleView: 'View version v{{versionNumber}}',
          titleEdit: 'Edit draft v{{versionNumber}}',
          titleClone: 'Create draft from v{{versionNumber}}',
          titleCreate: 'Create version',
          descReadonly: 'This version is published and read-only. To modify prompt, model or run strategy, go back and create a draft from it.',
          descEdit: 'Version details and Tool / MCP / Skill / Knowledge Base bindings are saved atomically in a single Agent Version request.',
          buttonClose: 'Close',
          buttonCancel: 'Cancel',
          buttonSubmitting: 'Submitting...',
          buttonSave: 'Save changes',
          buttonCreateDraft: 'Create draft',
          buttonCreate: 'Create version',
          loadingBindings: 'Loading Tool / Knowledge Base / MCP / Skill bindings...',
          modelLabel: 'Model',
          modelLoading: 'Loading...',
          modelPlaceholder: 'Select model',
          versionLabel: 'Version label',
          versionPlaceholder: 'e.g. v1-beta',
          localeLabel: 'Default locale',
          localePlaceholder: 'e.g. en-US',
          changelogLabel: 'Changelog',
          toolBindings: 'Tool bindings',
          addTool: 'Add tool',
          emptyToolBindings: 'No tool bindings added yet.',
          selectTool: 'Select tool',
          toolLabel: 'Tool #{{number}}',
          mcpBindings: 'MCP bindings',
          addMcpBinding: 'Add MCP binding',
          emptyMcpBindings: 'No MCP bindings added yet.',
          mcpLabel: 'MCP binding #{{number}}',
          selectMcpServer: 'Select MCP server',
          toolWhitelist: 'Tool whitelist',
          toolWhitelistPlaceholder: 'Leave empty to allow all tools; comma-separated',
          skillBindings: 'Skill bindings',
          addSkillBinding: 'Add skill binding',
          emptySkillBindings: 'No skill bindings added yet.',
          skillLabel: 'Skill binding #{{number}}',
          selectSkill: 'Select skill',
          configOverrides: 'Config overrides',
          toolOverrides: 'Tool overrides',
          addToolOverride: 'Add tool override',
          emptyToolOverrides: 'No tool overrides added yet.',
          toolOverrideLabel: 'Tool override #{{number}}',
          advancedPolicy: 'Advanced policy config',
          advancedPolicyHint: 'Advanced JSON policies below apply only to this agent version. Leave empty to use defaults.',
          agentLocalGuardrailsPolicyLabel: 'Agent-local Guardrails Policy',
          invocationModeAuto: 'Auto (model decides)',
          invocationModeManual: 'Manual only',
          invocationModeDisabled: 'Disabled',
          toolNameLabel: 'Tool name',
          toolDisplayNameLabel: 'Display name',
          toolDescriptionLabel: 'Description (override ToolSpec)',
          toolInvocationModeLabel: 'Invocation mode',
          toolRequiredLabel: 'Required tool',
          toolEnabledLabel: 'Enabled',
          mcpEnabledLabel: 'Enabled',
          skillKeyLabel: 'Skill',
          skillSortLabel: 'Sort order',
          skillEnabledLabel: 'Enabled'
        },
        kbBindings: {
          sectionTitle: 'Knowledge base bindings',
          addButton: 'Add knowledge base',
          readonlyInfo: 'This version is published; knowledge base bindings cannot be modified directly. Create a draft to make changes.',
          missingToolWarning: 'Knowledge bases are bound, but no usable knowledge_search tool is bound in this version; they will not be consumed at runtime.',
          emptyTitle: 'No knowledge bases bound',
          emptyDescription: 'After binding, knowledge_search can search within these bases in published versions.',
          drawerTitle: 'Add knowledge base binding',
          drawerDescription: 'Add a knowledge base scope to this draft version.',
          sortLabel: 'Sort order',
          enabledLabel: 'Enabled',
          selectLabel: 'Knowledge base',
          selectPlaceholder: 'Select knowledge base',
          saveButton: 'Save binding'
        }
      }
    },
    modelManagement: {
      label: 'Model management',
      summary: 'Manage connection profiles, models, instances, and bindings in one place.',
      eyebrow: 'AI Model Center',
      title: 'Model management',
      sections: {
        cards: 'Models',
        instances: 'Instances',
        bindings: 'Scenarios',
        profiles: 'Provider connections',
        features: 'Capabilities'
      },
      detail: {
        fallbackTitle: 'Model details',
        backToList: 'Back to model list',
        sections: {
          overview: 'Overview',
          instances: 'Instances',
          bindings: 'Bindings'
        }
      },
      errors: {
        connectionProfileKeyMismatch: 'Connection profile key mismatch. Please refresh and try again.',
        modelKeyMismatch: 'Model card key mismatch. Please refresh and try again.',
        instanceKeyMismatch: 'Instance key mismatch. Please refresh and try again.',
        bindingKeyMismatch: 'Binding key mismatch. Please refresh and try again.',
        unsupportedProvider: 'Unsupported provider type.',
        unsupportedScene: 'Unsupported business scene.',
        invalidJsonKind: 'Invalid format. Please check the JSON structure.',
        invalidJson: 'Invalid JSON. Please fix it and try again.',
        inUse: 'This item is currently in use and cannot be deleted.',
        alreadyExists: 'This identifier already exists. Please use a different name.',
        notFound: 'Item not found. It may have been deleted.'
      },
      featureValidation: {
        booleanRequired: 'Please select yes or no.',
        integerRequired: 'Please enter an integer.',
        numberRequired: 'Please enter a number.',
        enumRequired: 'Please select a valid option.'
      },
      shared: {
        enabledStatusOptions: {
          all: 'All statuses',
          enabledOnly: 'Enabled only',
          disabledOnly: 'Disabled only'
        },
        filterableOptions: {
          all: 'All filterable',
          filterableOnly: 'Filterable only',
          notFilterableOnly: 'Not filterable only'
        },
        routableOptions: {
          all: 'All routable',
          routableOnly: 'Routable only',
          notRoutableOnly: 'Not routable only'
        },
        healthStatusOptions: {
          all: 'All health statuses',
          healthyOnly: 'Healthy only',
          unhealthyOnly: 'Unhealthy only'
        }
      },
      models: {
        page: {
          newModel: 'New model',
          viewModeTable: 'Table',
          viewModeGrid: 'Grid',
          filterFeature: 'Capability',
          filterFeatureAll: 'All',
          filterEnableStatus: 'Status',
          emptyTitle: 'No models',
          createModel: 'Create model',
          deleteTitle: 'Delete model',
          deleteDescription: 'Delete model {{name}}?',
          confirmDelete: 'Confirm delete',
          columns: {
            displayName: 'Display name',
            instances: 'Instances',
            bindings: 'Bindings',
            features: 'Capabilities',
            status: 'Status',
            actions: 'Actions'
          },
          rowActions: {
            edit: 'Edit',
            detail: 'Details',
            test: 'Test',
            testEmbedding: 'Embedding Test',
            delete: 'Delete'
          },
          statsInstanceCount: '{{count}} instance(s)',
          statsInstanceCountWithHealth: '{{count}} instance(s) · {{healthy}} healthy',
          statsBindingCount: '{{count}} binding(s)',
          noFeature: 'No capabilities',
          status: {
            enabled: 'Enabled',
            disabled: 'Disabled'
          }
        },
        test: {
          title: 'Model Test',
          empty: 'Type a message to start testing. You can chat continuously. Each reply shows diagnostics: instance / time-to-first-token / duration / tokens.',
          inputPlaceholder: 'Type a test message...',
          send: 'Send',
          stop: 'Stop',
          generating: 'Generating...',
          diagnosis: {
            instanceKey: 'Instance',
            provider: 'Provider',
            ttft: 'TTFT',
            total: 'Total',
            inputTokens: 'In',
            outputTokens: 'Out',
            finishReason: 'Finish',
            error: 'Error',
            noData: '—'
          },
          errors: {
            noEnabledInstance: 'No enabled instance available for this model',
            upstreamError: 'Upstream call failed'
          }
        },
        embeddingTest: {
          title: 'Embedding Model Test — {{model}}',
          empty: 'Enter text and click Test to generate an embedding vector. Results show vector preview and diagnostics.',
          textLabel: 'Test Text',
          textPlaceholder: 'Enter text to vectorize...',
          dimensionsLabel: 'Dimensions (optional)',
          dimensionsPlaceholder: 'Default',
          dimensionsHint: 'Leave empty to use model default. Embedding-3 supports 256–2048.',
          close: 'Close',
          test: 'Test',
          testing: 'Testing...',
          provider: 'Provider',
          model: 'Model',
          dimensions: 'Dimensions',
          latency: 'Latency',
          tokens: 'Tokens',
          vectorPreview: 'Vector Preview',
          firstN: 'First {{n}}',
          unknownError: 'Unknown error'
        },
        drawer: {
          titleCreate: 'New model',
          titleEdit: 'Edit model',
          navigateToDetail: 'Go to detail after create',
          fields: {
            modelKey: 'Model key',
            type: 'Type',
            modelName: 'Model name',
            displayName: 'Display name',
            enableStatus: 'Status',
            description: 'Description',
            enabled: 'Enabled',
            disabled: 'Disabled',
            disabledBadge: ' (disabled)',
            connectionProfileKey: 'Connection profile',
            connectionProfileLoading: 'Loading...',
            connectionProfilePlaceholder: 'Select a connection'
          },
          features: {
            sectionTitle: 'Available capabilities',
            hint: 'These are the capability definitions available in the system. After creating the model, configure its capabilities on the detail page.',
            loading: 'Loading...',
            empty: 'No capabilities defined. Create one on the Capabilities page first.'
          },
          pricing: {
            sectionTitle: 'Pricing (per 1M tokens / USD)',
            inputPrice: 'Input Price',
            outputPrice: 'Output Price',
            cacheWritePrice: 'Cache Write Price',
            cacheReadPrice: 'Cache Read Price',
            unitHint: '$/MTok'
          },
          advanced: {
            sectionTitle: 'Advanced',
            tags: 'Tags',
            tagsHint: 'Tags for categorizing and searching.',
            routingPolicy: 'Routing policy',
            routingPolicyHint: 'Controls how requests are distributed across instances.',
            retryPolicy: 'Retry policy',
            retryPolicyHint: 'Auto-retry rules when a request fails.'
          },
          actions: {
            cancel: 'Cancel',
            submitting: 'Submitting...',
            create: 'Create model',
            save: 'Save changes'
          },
          validation: {
            modelKeyRequired: 'Please enter a model key.',
            modelNameRequired: 'Please enter a model name.',
            displayNameRequired: 'Please enter a display name.',
            connectionProfileKeyRequired: 'Please select a connection profile.'
          }
        },
        detail: {
          loading: 'Loading...',
          loadFailed: 'Failed to load. Please try again.',
          actions: {
            backToList: 'Back to list',
            addInstance: 'Add instance',
            addBinding: 'Add binding'
          },
          basicInfo: {
            cardTitle: 'Basic info',
            cardDescription: 'Core configuration of this model.',
            modelLabel: 'Model',
            modelKeyLabel: 'Model key',
            connectionProfileLabel: 'Connection profile',
            bindingsCount: 'Bindings',
            instancesCount: 'Instances',
            featureCount: 'Capabilities',
            statusLabel: 'Status',
            enabled: 'Enabled',
            disabled: 'Disabled',
            descriptionLabel: 'Description',
            noDescription: 'No description',
            countUnit: '{{count}}'
          },
          instances: {
            cardTitle: 'Instances',
            cardDescription: 'Each instance is a real model deployment. The system selects the best one based on priority and weight.',
            addButton: 'Add instance',
            stats: {
              total: 'Total',
              healthy: 'Healthy ratio',
              enabled: 'Enabled',
              regions: 'Regions'
            },
            fields: {
              deployName: 'Deployment',
              connection: 'Connection',
              region: 'Region',
              priority: 'Priority',
              weight: 'Weight',
              timeout: 'Timeout',
              type: 'Type'
            },
            status: {
              enabled: 'Enabled',
              disabled: 'Disabled',
              healthy: 'Healthy',
              unhealthy: 'Unhealthy'
            },
            defaultDeploy: 'Default deployment',
            defaultRegion: 'Default region',
            editButton: 'Edit',
            empty: 'No instances'
          },
          bindings: {
            cardTitle: 'Bindings',
            cardDescription: 'Assign this model to different business scenarios.',
            addButton: 'Add binding',
            empty: 'No bindings',
            status: {
              enabled: 'Enabled',
              disabled: 'Disabled'
            }
          }
        },
        featureSection: {
          cardTitle: 'Capabilities',
          configuredCount: '{{configured}} / {{total}} configured',
          configured: 'Configured',
          unconfigured: 'Unconfigured',
          loading: 'Loading capabilities...',
          empty: 'No configurable capabilities',
          disabled: 'Disabled',
          filterable: 'Filterable',
          routable: 'Affects routing',
          save: 'Save',
          saving: 'Saving...',
          remove: 'Remove',
          removing: 'Removing...',
          source: 'Source',
          remark: 'Remark',
          noFeature: 'No capabilities',
          dnd: {
            dragAriaLabel: 'Drag {{name}}',
            removeAriaLabel: 'Remove {{name}}',
            toggleAriaLabel: 'Toggle {{name}} support',
            addAriaLabel: 'Add {{name}}',
            edit: 'Edit',
            valueNotSet: '(not set)',
            valuePrefix: 'Value: ',
            add: 'Add',
            remove: 'Remove',
            unconfiguredTitle: 'Available',
            configuredTitle: 'Configured',
            unconfiguredEmpty: 'All capabilities added',
            configuredEmpty: 'Drag from the left to add',
            hint: 'Tip: Drag items or use the Add / Remove buttons. Click Edit to modify values.',
            editModal: {
              title: 'Edit capability',
              enableLabel: 'Enable this capability',
              featureValue: 'Value',
              booleanTrue: 'Yes',
              booleanFalse: 'No',
              source: 'Source',
              remark: 'Remark',
              cancel: 'Cancel',
              save: 'Save',
              saving: 'Saving...'
            }
          }
        },
        tabs: {
          loading: 'Loading...',
          loadFailed: 'Failed to load. Please try again.',
          instances: {
            description: 'Each instance is a real model deployment. The system selects the best one based on priority and weight.',
            addButton: 'Add instance',
            stats: {
              total: 'Total',
              healthy: 'Healthy ratio',
              enabled: 'Enabled',
              regions: 'Regions'
            },
            fields: {
              deployName: 'Deployment',
              connection: 'Connection',
              region: 'Region',
              priority: 'Priority',
              weight: 'Weight',
              timeout: 'Timeout',
              type: 'Type'
            },
            status: {
              enabled: 'Enabled',
              disabled: 'Disabled',
              healthy: 'Healthy',
              unhealthy: 'Unhealthy'
            },
            defaultDeploy: 'Default deployment',
            defaultRegion: 'Default region',
            editButton: 'Edit',
            empty: 'No instances'
          },
          bindings: {
            description: 'Assign this model to different business scenarios.',
            addButton: 'Add binding',
            empty: 'No bindings',
            status: {
              enabled: 'Enabled',
              disabled: 'Disabled'
            }
          },
          overview: {
            basicInfo: 'Basic info',
            modelLabel: 'Model',
            modelKeyLabel: 'Model key',
            bindingsCount: 'Bindings',
            instancesCount: 'Instances',
            featureCount: 'Capabilities',
            statusLabel: 'Status',
            enabled: 'Enabled',
            disabled: 'Disabled',
            descriptionLabel: 'Description',
            noDescription: 'No description',
            countUnit: '{{count}}',
            status: {
              enabled: 'Enabled',
              disabled: 'Disabled'
            }
          }
        },
        deleteDialog: {
          title: 'Delete model',
          description: 'Delete model {{name}}?',
          confirmLabel: 'Confirm delete'
        }
      },
      connectionProfiles: {
        page: {
          newProfile: 'New connection',
          columns: {
            profileKey: 'Connection name',
            endpoint: 'Endpoint',
            status: 'Status',
            actions: 'Actions'
          },
          filters: {
            provider: 'Provider',
            allProviders: 'All providers',
            enableStatus: 'Status'
          },
          emptyTitle: 'No connections',
          status: {
            enabled: 'Enabled',
            disabled: 'Disabled'
          },
          rowActions: {
            edit: 'Edit',
            delete: 'Delete'
          },
          deleteTitle: 'Delete connection',
          deleteDescription: 'Delete connection {{name}}?',
          confirmDelete: 'Confirm delete'
        },
        drawer: {
          titleCreate: 'New connection',
          titleEdit: 'Edit connection',
          description: 'Fill in the AI provider access information. Advanced parameters are at the bottom.',
          fields: {
            profileKey: 'Connection key',
            displayName: 'Display name',
            baseUrl: 'Base URL',
            baseUrlHint: 'The root API URL of the AI provider. E.g. OpenAI: https://api.openai.com/v1/, Azure OpenAI: https://{resource}.openai.azure.com/openai/',
            wsUrl: 'WebSocket URL',
            wsUrlHint: 'For real-time voice and WebSocket scenarios. Usually not needed unless the provider has a separate WebSocket endpoint.',
            apiVersion: 'API version',
            apiVersionHint: 'Some providers (e.g. Azure OpenAI) require an API version such as 2025-04-01-preview. Typically not needed for OpenAI.',
            apiVersionPlaceholder: 'e.g. 2025-04-01-preview',
            enableConnection: 'Enable this connection',
            extraJson: 'Extra parameters',
            extraJsonHint: 'Provider-specific extra configuration.'
          },
          advanced: {
            sectionTitle: 'Advanced',
            collapse: 'Collapse',
            expand: 'Expand'
          },
          actions: {
            cancel: 'Cancel',
            submitting: 'Submitting...',
            create: 'Create connection',
            save: 'Save changes'
          },
          validation: {
            profileKeyRequired: 'Please enter a connection key.',
            displayNameRequired: 'Please enter a display name.'
          }
        }
      },
      featureDefinitions: {
        page: {
          newFeature: 'New capability',
          columns: {
            featureKey: 'Capability name',
            valueType: 'Data type',
            flags: 'Flags',
            status: 'Status',
            actions: 'Actions'
          },
          filters: {
            valueType: 'Data type',
            allTypes: 'All types',
            enableStatus: 'Status',
            filterable: 'Filterable',
            routable: 'Routable'
          },
          flags: {
            filterable: 'Filterable',
            routable: 'Affects routing'
          },
          status: {
            enabled: 'Enabled',
            disabled: 'Disabled'
          },
          rowActions: {
            edit: 'Edit',
            delete: 'Delete'
          },
          emptyTitle: 'No capabilities',
          deleteTitle: 'Delete capability',
          deleteDescription: 'Delete capability {{name}}?',
          confirmDelete: 'Confirm delete',
          createNow: 'Create now'
        },
        drawer: {
          titleCreate: 'New capability',
          titleEdit: 'Edit capability',
          description: 'Define capability labels that models can declare, used for filtering and routing.',
          fields: {
            featureKey: 'Capability key',
            displayName: 'Display name',
            valueType: 'Data type',
            description: 'Description',
            allowedValues: 'Allowed values',
            allowedValuesHint: 'Used only when the type is enum. Defines the list of valid values.',
            isFilterable: 'Filterable',
            isRoutable: 'Affects routing',
            isEnabled: 'Enabled'
          },
          actions: {
            cancel: 'Cancel',
            submitting: 'Submitting...',
            create: 'Create capability',
            save: 'Save changes'
          },
          validation: {
            featureKeyRequired: 'Please enter a capability key.',
            displayNameRequired: 'Please enter a display name.',
            valueTypeRequired: 'Please select a data type.'
          }
        }
      },
      modelBindings: {
        page: {
          newBinding: 'New binding',
          columns: {
            bindingKey: 'Binding name',
            usage: 'Usage',
            mapping: 'Capability / Model',
            status: 'Status',
            actions: 'Actions'
          },
          filters: {
            capability: 'Capability',
            allCapabilities: 'All capabilities',
            modelKey: 'Model',
            enableStatus: 'Status'
          },
          status: {
            enabled: 'Enabled',
            disabled: 'Disabled'
          },
          rowActions: {
            edit: 'Edit',
            delete: 'Delete'
          },
          emptyTitle: 'No bindings',
          createBinding: 'Create binding',
          deleteTitle: 'Delete binding',
          deleteDescription: 'Delete binding {{name}}?',
          confirmDelete: 'Confirm delete'
        },
        drawer: {
          titleCreate: 'New binding',
          titleEdit: 'Edit binding',
          description: 'Assign a model to a business scenario.',
          fields: {
            bindingKey: 'Binding key',
            displayName: 'Display name',
            preset: 'Usage template',
            presetHint: 'Picking one auto-fills the capability below; you can still adjust it manually.',
            capability: 'Capability',
            modelKey: 'Model',
            modelKeyLoading: 'Loading...',
            modelKeyPlaceholder: 'Select a model',
            enableBinding: 'Enable this binding',
            metadataJson: 'Extra parameters',
            metadataJsonHint: 'Scene-specific extra configuration.'
          },
          actions: {
            cancel: 'Cancel',
            submitting: 'Submitting...',
            create: 'Create binding',
            save: 'Save changes'
          },
          validation: {
            bindingKeyRequired: 'Please enter a binding key.',
            displayNameRequired: 'Please enter a display name.',
            modelKeyRequired: 'Please select a model.'
          }
        }
      },
      modelInstances: {
        page: {
          newInstance: 'New instance',
          columns: {
            instanceKey: 'Instance',
            modelName: 'Model name',
            connectionProfileKey: 'Connection',
            priority: 'Priority / Weight / Timeout',
            status: 'Status',
            actions: 'Actions'
          },
          filters: {
            modelKey: 'Model',
            connectionProfileKey: 'Connection',
            feature: 'Capability',
            featureAll: 'All',
            featureSupport: 'Support',
            featureSupportAll: 'All',
            featureSupportTrue: 'Supported',
            featureSupportFalse: 'Not supported',
            featureValue: 'Capability value',
            type: 'Type',
            typeAll: 'All types',
            loading: 'Loading...',
            enableStatus: 'Status',
            healthStatus: 'Health'
          },
          metrics: {
            total: 'Total',
            totalHint: 'Total instances matching filters',
            enabled: 'Enabled',
            enabledHint: 'Enabled instances on this page',
            healthy: 'Healthy',
            healthyHint: 'Healthy instances on this page',
            typeCount: 'Types',
            typeCountHint: 'Distinct capability types on this page'
          },
          status: {
            enabled: 'Enabled',
            disabled: 'Disabled',
            healthy: 'Healthy',
            unhealthy: 'Unhealthy'
          },
          rowActions: {
            edit: 'Edit',
            delete: 'Delete'
          },
          emptyTitle: 'No instances',
          createInstance: 'Create instance',
          deleteTitle: 'Delete instance',
          deleteDescription: 'Delete instance {{name}}?',
          confirmDelete: 'Confirm delete'
        },
        drawer: {
          titleCreate: 'New instance',
          titleEdit: 'Edit instance',
          description: 'An instance represents a real model deployment. Capability config is inherited from the model; connection config is set per instance.',
          fields: {
            modelKey: 'Model',
            modelKeyLoading: 'Loading...',
            modelKeyPlaceholder: 'Select a model',
            instanceKey: 'Instance key',
            connectionProfileKey: 'Connection',
            connectionProfileLoading: 'Loading...',
            connectionProfilePlaceholder: 'Select a connection',
            deploymentName: 'Deployment name',
            region: 'Region',
            priority: 'Priority',
            weight: 'Weight',
            timeout: 'Default timeout (ms)',
            apiKey: 'API key',
            apiKeyHintEdit: 'Leave blank to keep the current key.',
            apiKeyHintCreate: 'Will not be shown again after submission.',
            apiKeyPlaceholderEdit: 'Leave blank to keep current',
            instanceUrl: 'Instance URL',
            instanceUrlHint: 'Determined by the selected connection. Read-only.',
            isEnabled: 'Enable instance',
            isHealthy: 'Health',
            extraJson: 'Extra parameters',
            extraJsonHint: 'Instance-specific extra configuration.',
            advancedOptions: 'Advanced options'
          },
          actions: {
            cancel: 'Cancel',
            submitting: 'Submitting...',
            create: 'Create instance',
            save: 'Save changes'
          },
          validation: {
            modelKeyRequired: 'Please select a model.',
            instanceKeyRequired: 'Please enter an instance key.',
            connectionProfileKeyRequired: 'Please select a connection.',
            priorityMin: 'Priority must be ≥ 0.',
            weightMin: 'Weight must be > 0.',
            timeoutMin: 'Default timeout must be > 0.',
            apiKeyRequired: 'Please enter an API key.'
          }
        }
      },
      instancesByModel: {
        modelList: 'Model list',
        noModels: 'No models',
        selectModel: 'Select a model',
        selectModelHint: 'Choose a model from the list to view its instances',
        instancesTitle: '{{count}} instances',
        noInstances: 'No instances',
        emptyTitle: 'No instances for this model',
        emptyDescription: 'Click the button above to create the first instance.',
        instanceCount: '{{count}} instances'
      }
    },
    glossary: {
      label: 'Glossary',
      summary: 'Manage glossary categories and terms, then bind them to knowledge bases.',
      eyebrow: 'Knowledge augmentation',
      title: 'Glossary',
      sections: {
        list: 'Glossary management'
      },
      list: {
        title: 'Glossary',
        description: 'Manage glossary categories and terms, then bind them to knowledge bases.',
        newCategory: 'New category',
        searchLabel: 'Search',
        searchPlaceholder: 'Category name...',
        emptyTitle: 'No glossary categories',
        emptyDescription: 'Click "New category" to get started.',
        deleteTitle: 'Delete category',
        deleteDescription: 'Are you sure you want to delete category "{{name}}"?',
        confirmDelete: 'Delete category'
      },
      categoryForm: {
        titleCreate: 'New category',
        titleEdit: 'Edit category',
        description: 'Categories group glossary terms and serve as the smallest knowledge base binding unit.',
        fields: {
          name: 'Category name',
          namePlaceholder: 'For example: RAG',
          description: 'Description',
          descriptionPlaceholder: 'Optional. Describe when this category should be used.'
        },
        actions: {
          cancel: 'Cancel',
          submitting: 'Saving...',
          create: 'Create category',
          save: 'Save'
        },
        validation: {
          nameRequired: 'Please enter a category name.'
        }
      },
      category: {
        fallbackTitle: 'Glossary category',
        eyebrow: 'Glossary',
        backToList: 'Back to glossary',
        sections: {
          terms: 'Terms'
        }
      },
      categoryCard: {
        menuLabel: 'Category actions',
        actions: {
          edit: 'Edit',
          delete: 'Delete'
        }
      },
      categoryItem: {
        descriptionFallback: 'No category description',
        actions: {
          edit: 'Edit',
          delete: 'Delete'
        }
      },
      termsTab: {
        columns: {
          term: 'Term',
          synonyms: 'Synonyms',
          createdAt: 'Created at',
          actions: 'Actions'
        },
        rowActions: {
          edit: 'Edit',
          delete: 'Delete'
        },
        toolbar: {
          import: 'Import terms',
          create: 'New term',
          searchLabel: 'Search',
          searchPlaceholder: 'Search terms or synonyms...'
        },
        emptyTitle: 'No terms',
        emptyDescription: 'There are no terms in this category yet. Add one manually or import a file.',
        emptyAction: 'Add term',
        deleteTitle: 'Delete term',
        deleteDescription: 'Are you sure you want to delete term "{{name}}"?',
        confirmDelete: 'Delete term'
      },
      termForm: {
        titleCreate: 'New term',
        titleEdit: 'Edit term',
        description: 'Terms and synonyms are used for glossary matching, imports, and knowledge base bindings.',
        fields: {
          category: 'Category',
          categoryPlaceholder: 'Please select a category',
          term: 'Term',
          termPlaceholder: 'For example: Embedding',
          synonyms: 'Synonyms',
          synonymsHint: 'Enter one synonym per line, or separate them with commas.',
          synonymsPlaceholder: 'For example: Vectorization'
        },
        actions: {
          cancel: 'Cancel',
          submitting: 'Saving...',
          create: 'Create term',
          save: 'Save'
        },
        validation: {
          categoryRequired: 'Please select a category.',
          termRequired: 'Please enter a term name.'
        }
      },
      termImport: {
        title: 'Import terms',
        description: 'Upload a CSV file to import terms and review row-level errors.',
        actions: {
          cancel: 'Cancel',
          importing: 'Importing...',
          submit: 'Import terms',
          downloadTemplate: 'Download import template'
        },
        upload: {
          replaceFile: 'Click to choose another file',
          selectFile: 'Click to upload a file',
          hint: 'Supports .csv and .xlsx files'
        },
        template: {
          prompt: 'Need a template?'
        },
        result: {
          importedCount: 'Imported {{count}} terms',
          noErrors: 'No row-level errors were returned.'
        },
        errorFallback: 'Import failed. Please try again later.'
      },
      termItem: {
        noSynonyms: 'No synonyms',
        actions: {
          edit: 'Edit',
          delete: 'Delete'
        }
      }
    },
    knowledgeBase: {
      label: 'Knowledge base',
      summary: 'Manage knowledge bases, upload documents, and run retrieval tests.',
      title: 'Knowledge base',
      list: {
        title: 'Knowledge base',
        description: 'Manage knowledge bases, upload documents, and test search results.',
        create: 'Create knowledge base',
        searchLabel: 'Search',
        searchPlaceholder: 'Knowledge base name...',
        statusLabel: 'Status',
        statuses: {
          all: 'All',
          active: 'Active',
          processing: 'Processing',
          disabled: 'Disabled'
        },
        emptyTitle: 'No knowledge bases',
        emptyDescription: 'Click "Create knowledge base" to get started.',
        deleteTitle: 'Delete knowledge base',
        deleteDescription: 'Are you sure you want to delete "{{name}}"?'
      },
      detail: {
        eyebrow: 'Knowledge base',
        fallbackTitle: 'Knowledge base',
        backToList: 'Back to knowledge base list',
        updateSuccess: 'Knowledge base updated',
        updateFailed: 'Failed to update knowledge base',
        sections: {
          overview: 'Overview',
          documents: 'Documents',
          glossary: 'Glossary bindings',
          search: 'Search test'
        },
        glossaryBindingDescription: 'Select glossary categories to participate in term matching for this knowledge base. Saving will overwrite the existing bindings.',
        glossarySave: 'Save bindings',
        glossarySaving: 'Saving...',
        glossaryDescriptionFallback: 'No description provided',
        glossaryRefreshFailed: 'Failed to refresh latest state; showing cached results.',
        glossaryEmptyTitle: 'No glossary categories',
        glossaryEmptyDescription: 'Create categories in the Glossary module first, then come back to bind them to this knowledge base.',
        segmentEmptyTitle: 'No segments',
        folderEmptyTitle: 'No folders'
      }
    },
    modelMonitoring: {
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
    },
    costAnalysis: {
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
    },
    observability: {
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
    },
    memory: {
      label: 'Memory',
      summary: 'Manage AI Agent memory storage.',
      eyebrow: 'Memory',
      title: 'Memory',
      sections: {
        memories: 'Memory List'
      },
      list: {
        title: 'Memory List',
        description: 'Manage Agent long-term memory and context.',
        searchPlaceholder: 'Search memory...',
        emptyTitle: 'No memory data',
        emptyDescription: 'Memory data will appear here once the Agent starts interacting.',
        filterAll: 'All',
        typeLabels: {
          episodic: 'Episodic',
          semantic: 'Semantic',
          procedural: 'Procedural'
        },
        accessCount: '{{count}} accesses',
        relevance: 'Relevance {{score}}',
        deactivate: 'Deactivate',
        consolidate: 'Consolidate',
        prevPage: 'Previous',
        nextPage: 'Next',
        pageInfo: 'Page {{page}} / {{total}}',
        metrics: {
          totalActive: 'Total',
          episodic: 'Episodic',
          semantic: 'Semantic',
          procedural: 'Procedural'
        },
        loadError: 'Failed to load memories. Please refresh.',
        filterLabel: 'Filter memories by type'
      }
    },
    evaluation: {
      label: 'Evaluation',
      summary: 'Manage evaluation datasets and runs.',
      eyebrow: 'Evaluation',
      title: 'Evaluation',
      sections: {
        datasets: 'Datasets',
        runs: 'Evaluation runs'
      },
      datasets: {
        title: 'Datasets',
        description: 'Manage evaluation datasets for testing and evaluating model performance.',
        createDataset: 'Create dataset',
        emptyTitle: 'No datasets',
        emptyDescription: 'Click "Create dataset" to get started.',
        columns: {
          name: 'Dataset name',
          description: 'Description',
          itemCount: 'Item count',
          createdAt: 'Created at',
          actions: 'Actions'
        },
        actions: {
          view: 'View',
          edit: 'Edit',
          delete: 'Delete'
        }
      },
      runs: {
        title: 'Evaluation runs',
        description: 'View evaluation run records and results.',
        emptyTitle: 'No evaluation runs',
        emptyDescription: 'Run records will appear here once evaluation starts.',
        columns: {
          runId: 'Run ID',
          dataset: 'Dataset',
          model: 'Model',
          status: 'Status',
          score: 'Score',
          startedAt: 'Started at',
          completedAt: 'Completed at'
        },
        status: {
          pending: 'Pending',
          running: 'Running',
          completed: 'Completed',
          failed: 'Failed'
        }
      }
    }
  }
} as const;
