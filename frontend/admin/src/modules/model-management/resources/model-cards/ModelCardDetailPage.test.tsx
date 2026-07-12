import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { ModelDetailLayout } from '../../pages/ModelCardDetailLayout';
import { ModelOverviewTab } from './tabs/ModelCardOverviewTab';
import { ModelInstancesTab } from './tabs/ModelCardInstancesTab';
import { ModelBindingsTab } from './tabs/ModelCardBindingsTab';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockCardFetch(overrides: { instances?: object[]; bindings?: object[]; features?: object[] } = {}) {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;

    if (url.includes('/api/llm-catalog/features/options')) {
      return Promise.resolve(new Response(JSON.stringify({ success: true, msg: 'ok', data: [] }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      }));
    }

    if (url.includes('/api/llm-catalog/options/models')) {
      return Promise.resolve(new Response(JSON.stringify({
        success: true, msg: 'ok',
        data: [{ modelKey: 'voice.agent', displayName: 'Voice Agent', isEnabled: true }],
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }

    if (url.includes('/api/llm-catalog/options/connection-profiles')) {
      return Promise.resolve(new Response(JSON.stringify({
        success: true, msg: 'ok',
        data: [{
          profileKey: 'openai.primary', displayName: 'OpenAI Primary', provider: 'openai',
          baseUrl: 'https://api.openai.com/v1', webSocketBaseUrl: null, isEnabled: true,
        }],
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }

    if (url.includes('/api/llm-catalog/models/') && url.endsWith('/instances')) {
      const items = overrides.instances ?? [{
        modelKey: 'voice.agent', instanceKey: 'voice-main',
        type: 'Text', modelName: 'gpt-4.1-mini', providerDeploymentName: null, region: null,
        priority: 1, weight: 100, defaultTimeoutMs: 30000, extraJson: '{}', isEnabled: true, isHealthy: true,
      }];
      return Promise.resolve(new Response(JSON.stringify({
        success: true, msg: 'ok',
        data: { items, page: 1, pageSize: 20, totalCount: (items as object[]).length },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }

    return Promise.resolve(new Response(JSON.stringify({
      success: true, msg: 'ok',
      data: {
        modelKey: 'voice.agent', type: 'Text', modelName: 'gpt-4.1-mini',
        displayName: 'Voice Agent', description: 'Voice capabilities',
        connectionProfileKey: 'openai.primary',
        tagsJson: '["voice"]', routingPolicyJson: '{}', retryPolicyJson: '{}', isEnabled: true,
        instances: overrides.instances ?? [{
          modelKey: 'voice.agent', instanceKey: 'voice-main',
          type: 'Text', modelName: 'gpt-4.1-mini', providerDeploymentName: null, region: null,
          priority: 1, weight: 100, defaultTimeoutMs: 30000, extraJson: '{}', isEnabled: true, isHealthy: true,
        }],
        bindings: overrides.bindings ?? [{
          bindingKey: 'voice.default', displayName: 'Voice Default',
          capability: 'Text', modelKey: 'voice.agent', metadataJson: '{}', isEnabled: true,
        }],
        features: overrides.features ?? [{
          modelKey: 'voice.agent', featureKey: 'function_call', displayName: 'Function Call',
          valueType: 'boolean', allowedValuesJson: '[]', isSupported: true,
          valueJson: 'true', source: 'manual', remark: null,
        }],
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
  });
}

function renderDetailRoutes(initialPath = '/model-management/models/voice.agent') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/model-management/models/:modelKey" element={<ModelDetailLayout />}>
          <Route index element={<ModelOverviewTab />} />
          <Route path="instances" element={<ModelInstancesTab />} />
          <Route path="bindings" element={<ModelBindingsTab />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ModelDetailLayout', () => {
  afterEach(() => { vi.restoreAllMocks(); });

  it('renders layout header with card name and tab navigation', async () => {
    mockCardFetch();
    renderDetailRoutes();

    expect(await screen.findByRole('heading', { name: 'Voice Agent' })).toBeInTheDocument();
    expect(screen.getAllByText('基本信息').length).toBeGreaterThan(0);
    expect(screen.getAllByText('部署实例').length).toBeGreaterThan(0);
    expect(screen.getAllByText('场景绑定').length).toBeGreaterThan(0);
  });
});

describe('ModelOverviewTab', () => {
  afterEach(() => { vi.restoreAllMocks(); });

  it('shows card meta info and features', async () => {
    mockCardFetch();
    renderDetailRoutes();

    expect(await screen.findByRole('heading', { name: 'Voice Agent' })).toBeInTheDocument();
    expect(screen.getByText('模型能力')).toBeInTheDocument();
    expect(screen.getAllByText(/Function Call/).length).toBeGreaterThan(0);
  });
});

describe('ModelInstancesTab', () => {
  afterEach(() => { vi.restoreAllMocks(); });

  it('renders instance list', async () => {
    mockCardFetch();
    renderDetailRoutes('/model-management/models/voice.agent/instances');

    expect(await screen.findByText('voice-main')).toBeInTheDocument();
  });

  it('opens the edit instance drawer with existing extraJson', async () => {
    mockCardFetch({
      instances: [{
        modelKey: 'voice.agent', instanceKey: 'voice-main',
        type: 'Text', modelName: 'gpt-5', providerDeploymentName: 'gpt-5', region: null,
        priority: 1, weight: 100, defaultTimeoutMs: 30000,
        extraJson: '{\n  "temperature": 0.2\n}', isEnabled: true, isHealthy: true,
      }],
      bindings: [], features: [],
    });
    renderDetailRoutes('/model-management/models/voice.agent/instances');

    expect(await screen.findByRole('button', { name: '编辑' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '编辑' }));

    expect((screen.getByLabelText('扩展参数') as HTMLTextAreaElement).value).toContain('"temperature": 0.2');
  });

  it('resets the form when closing one instance drawer and opening another', async () => {
    mockCardFetch({
      instances: [
        {
          modelKey: 'voice.agent', instanceKey: 'voice-main',
          type: 'Text', modelName: 'gpt-5', providerDeploymentName: 'gpt-5', region: null,
          priority: 1, weight: 100, defaultTimeoutMs: 30000, extraJson: '{}', isEnabled: true, isHealthy: true,
        },
        {
          modelKey: 'voice.agent', instanceKey: 'voice-secondary',
          type: 'Text', modelName: 'gpt-5', providerDeploymentName: 'gpt-5-secondary', region: null,
          priority: 2, weight: 100, defaultTimeoutMs: 30000, extraJson: '{}', isEnabled: true, isHealthy: true,
        },
      ],
      bindings: [], features: [],
    });
    renderDetailRoutes('/model-management/models/voice.agent/instances');

    expect(await screen.findByRole('heading', { name: 'Voice Agent' })).toBeInTheDocument();

    // Open drawer for first instance
    const editButtons = await screen.findAllByRole('button', { name: /编辑|缂栬緫/ });
    fireEvent.click(editButtons[0]);
    expect(await screen.findByDisplayValue('voice-main')).toBeInTheDocument();

    // Close and open drawer for second instance
    fireEvent.click(screen.getByRole('button', { name: /关闭|鍏抽棴/ }));
    const editButtonsAfterClose = await screen.findAllByRole('button', { name: /编辑|缂栬緫/ });
    fireEvent.click(editButtonsAfterClose[1]);
    expect(await screen.findByDisplayValue('voice-secondary')).toBeInTheDocument();
  });
});

describe('ModelBindingsTab', () => {
  afterEach(() => { vi.restoreAllMocks(); });

  it('renders binding list', async () => {
    mockCardFetch();
    renderDetailRoutes('/model-management/models/voice.agent/bindings');

    expect(await screen.findByText('Voice Default')).toBeInTheDocument();
  });
});

