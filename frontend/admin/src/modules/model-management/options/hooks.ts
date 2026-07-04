import { useQuery } from '@tanstack/react-query';
import { modelManagementStaleTime } from '../lib/queryKeys';
import { getProviderModelOptions, listConnectionProfileOptions, listFeatureOptions, listModelOptions } from './api';

export function useModelOptions(enabled = true) {
  return useQuery({
    queryKey: ['model-management', 'options', 'models'],
    queryFn: listModelOptions,
    staleTime: modelManagementStaleTime.options,
    enabled,
  });
}

export function useConnectionProfileOptions(enabled = true) {
  return useQuery({
    queryKey: ['model-management', 'options', 'connection-profiles'],
    queryFn: listConnectionProfileOptions,
    staleTime: modelManagementStaleTime.options,
    enabled,
  });
}

export function useProviderModelOptions(connectionProfileKey: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['model-management', 'options', 'provider-models', connectionProfileKey],
    queryFn: () => getProviderModelOptions(connectionProfileKey!),
    staleTime: modelManagementStaleTime.options,
    enabled: enabled && Boolean(connectionProfileKey),
  });
}

export function useFeatureOptions(enabled = true) {
  return useQuery({
    queryKey: ['model-management', 'options', 'features'],
    queryFn: listFeatureOptions,
    staleTime: modelManagementStaleTime.options,
    enabled,
  });
}

// Backward-compatible re-export
export { useFeatureOptions as useFeatureDefinitionOptions };
