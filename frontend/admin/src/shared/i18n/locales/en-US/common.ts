// Auto-generated — do not edit manually
export const common = {
  userMenu: {
    ariaLabel: 'User menu',
    account: 'Account',
    language: 'Language',
    languageTitle: 'Choose language',
    preferences: 'Preferences',
    preferencesTitle: 'Preferences',
    profile: 'Profile',
    changePassword: 'Change password',
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
    userManagement: 'User management',
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
  shared: {
    auth: {
      profile: {
        title: 'Profile',
        username: 'Username',
        displayName: 'Display name',
        email: 'Email',
        save: 'Save',
        saving: 'Saving...'
      },
      changePassword: {
        title: 'Change password',
        currentPassword: 'Current password',
        newPassword: 'New password',
        confirmPassword: 'Confirm new password',
        save: 'Change password',
        saving: 'Changing...',
        tooShort: 'Password must be at least 8 characters.',
        mismatch: 'Passwords do not match.'
      }
    }
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
} as const;
