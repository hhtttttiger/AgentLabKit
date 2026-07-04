/**
 * Model Test Dialog - SSE event & diagnosis types.
 *
 * 对应后端 `POST /api/ai/invoke/{model_id}/text/test-stream` 的事件协议。
 */

export type ModelTestStreamEvent =
  | {
      type: 'content';
      content: string;
      instance_key?: string | null;
      provider?: string | null;
      model?: string | null;
    }
  | {
      type: 'stats';
      ttft_ms: number | null;
      total_ms: number;
      instance_key?: string | null;
      provider?: string | null;
      model?: string | null;
      finish_reason?: string | null;
      input_tokens?: number | null;
      output_tokens?: number | null;
      total_tokens?: number | null;
    }
  | {
      type: 'error';
      message: string;
      code?: string | null;
      ttft_ms?: number | null;
      total_ms?: number;
    };

/** 单轮对话的诊断汇总（实例 / 延迟 / token / 错误）。 */
export interface ModelTestDiagnosis {
  instanceKey?: string;
  provider?: string;
  model?: string;
  ttftMs?: number | null;
  totalMs?: number;
  finishReason?: string | null;
  inputTokens?: number | null;
  outputTokens?: number | null;
  totalTokens?: number | null;
  errorMessage?: string;
  errorCode?: string | null;
}

export interface ModelTestContentMeta {
  instanceKey?: string;
  provider?: string;
  model?: string;
}

export interface ModelTestStreamCallbacks {
  onContent: (delta: string, meta: ModelTestContentMeta) => void;
  onStats: (diagnosis: ModelTestDiagnosis) => void;
  onError: (diagnosis: ModelTestDiagnosis) => void;
  onComplete: () => void;
}

/** Embedding 模型测试结果。 */
export interface EmbeddingTestResult {
  success: boolean;
  provider?: string | null;
  model?: string | null;
  dimensions?: number;
  vectorPreview?: number[];
  vectorPreviewTruncated?: boolean;
  usage?: {
    input_tokens?: number;
    total_tokens?: number;
  } | null;
  latencyMs?: number;
  error?: {
    message: string;
    code?: string | null;
  } | null;
}
