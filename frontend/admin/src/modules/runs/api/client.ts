import { apiRequest } from '@/shared/api/client';
import type {
  CaptureRunRequest, CaptureRunResponse, ReplayRunDto, RunDetailDto,
} from './dto';

/** Durable Runtime Run endpoints exposed by FastAPI Adapter v1. */
export function getRun(runId: string): Promise<RunDetailDto> {
  return apiRequest<RunDetailDto>(`/api/runs/${encodeURIComponent(runId)}`);
}

export function replayRun(runId: string): Promise<ReplayRunDto> {
  return apiRequest<ReplayRunDto>(`/api/runs/${encodeURIComponent(runId)}/replay`, { method: 'POST' });
}

export function captureRun(runId: string, request: CaptureRunRequest): Promise<CaptureRunResponse> {
  return apiRequest<CaptureRunResponse>(`/api/runs/${encodeURIComponent(runId)}/capture`, {
    method: 'POST', body: request,
  });
}

