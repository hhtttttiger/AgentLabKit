// Auto-generated — do not edit manually
export const modelManagement = {
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
} as const;
