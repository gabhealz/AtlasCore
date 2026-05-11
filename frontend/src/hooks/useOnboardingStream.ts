import { useEffect, useRef, useState, type RefObject } from 'react';

import { api } from '../lib/api';
import { useAuthStore } from '../store/auth';

export type PipelineStreamEvent = {
  onboarding_id: number;
  step_name: string;
  from_status: string;
  to_status: string;
  trigger: string;
  created_at: string;
  attempt_count?: number;
  error_code?: string;
  error_message?: string;
  agent_name?: string;
  model?: string;
  document_kind?: string;
  review_round?: number;
  reviewed_agent?: string;
  issues?: string[];
  quality_feedback?: string;
  document_title?: string;
};

export type StreamConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'unavailable';

type UseOnboardingStreamOptions = {
  onboardingId: number;
  enabled?: boolean;
  onEventRef?: RefObject<((event: PipelineStreamEvent) => void) | null>;
};

type StreamProbeResult = 'ok' | 'terminal' | 'network_error' | 'aborted';

const STREAM_PROBE_TIMEOUT_MS = 8000;

function parsePipelineStreamEvent(rawData: string): PipelineStreamEvent | null {
  try {
    const parsedData = JSON.parse(rawData) as Partial<PipelineStreamEvent>;
    if (
      typeof parsedData.onboarding_id !== 'number' ||
      typeof parsedData.step_name !== 'string' ||
      typeof parsedData.from_status !== 'string' ||
      typeof parsedData.to_status !== 'string' ||
      typeof parsedData.trigger !== 'string' ||
      typeof parsedData.created_at !== 'string'
    ) {
      return null;
    }

    if (
      parsedData.attempt_count !== undefined &&
      typeof parsedData.attempt_count !== 'number'
    ) {
      return null;
    }

    if (
      parsedData.error_code !== undefined &&
      typeof parsedData.error_code !== 'string'
    ) {
      return null;
    }

    if (
      parsedData.error_message !== undefined &&
      typeof parsedData.error_message !== 'string'
    ) {
      return null;
    }

    if (
      parsedData.agent_name !== undefined &&
      typeof parsedData.agent_name !== 'string'
    ) {
      return null;
    }

    if (parsedData.model !== undefined && typeof parsedData.model !== 'string') {
      return null;
    }

    if (
      parsedData.document_kind !== undefined &&
      typeof parsedData.document_kind !== 'string'
    ) {
      return null;
    }

    if (
      parsedData.review_round !== undefined &&
      typeof parsedData.review_round !== 'number'
    ) {
      return null;
    }

    if (
      parsedData.reviewed_agent !== undefined &&
      typeof parsedData.reviewed_agent !== 'string'
    ) {
      return null;
    }

    if (
      parsedData.issues !== undefined &&
      (!Array.isArray(parsedData.issues) ||
        !parsedData.issues.every((issue) => typeof issue === 'string'))
    ) {
      return null;
    }

    if (
      parsedData.quality_feedback !== undefined &&
      typeof parsedData.quality_feedback !== 'string'
    ) {
      return null;
    }

    if (
      parsedData.document_title !== undefined &&
      typeof parsedData.document_title !== 'string'
    ) {
      return null;
    }

    return parsedData as PipelineStreamEvent;
  } catch {
    return null;
  }
}

function buildStreamUrl(onboardingId: number, token: string) {
  const baseUrl = api.defaults.baseURL?.replace(/\/$/, '');
  if (!baseUrl) {
    return null;
  }

  const browserOrigin =
    typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
  const streamUrl = new URL(
    `${baseUrl}/onboardings/${onboardingId}/stream`,
    browserOrigin,
  );
  streamUrl.searchParams.set('access_token', token);
  return streamUrl.toString();
}

async function probeStreamAvailability(
  streamUrl: string,
  signal: AbortSignal,
): Promise<StreamProbeResult> {
  if (signal.aborted) {
    return 'aborted';
  }

  const probeController = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const abortProbe = () => {
    probeController.abort();
  };
  signal.addEventListener('abort', abortProbe, { once: true });

  try {
    timeoutId = setTimeout(() => {
      probeController.abort();
    }, STREAM_PROBE_TIMEOUT_MS);
    const response = await fetch(streamUrl, {
      headers: {
        Accept: 'text/event-stream',
        Authorization: `Bearer ${useAuthStore.getState().token ?? ''}`,
      },
      credentials: 'include',
      signal: probeController.signal,
    });
    const contentType = response.headers.get('content-type') ?? '';
    const isEventStream =
      response.ok && contentType.includes('text/event-stream');

    void response.body?.cancel();
    return isEventStream ? 'ok' : 'terminal';
  } catch {
    if (signal.aborted) {
      return 'aborted';
    }

    return 'network_error';
  } finally {
    signal.removeEventListener('abort', abortProbe);
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

export function useOnboardingStream({
  onboardingId,
  enabled = true,
  onEventRef,
}: UseOnboardingStreamOptions) {
  const token = useAuthStore((state) => state.token);
  const [connectionStatus, setConnectionStatus] = useState<{
    onboardingId: number | null;
    status: StreamConnectionStatus;
  }>({
    onboardingId: null,
    status: 'idle',
  });
  const [latestEvent, setLatestEvent] = useState<PipelineStreamEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const hasConnectedOnceRef = useRef(false);
  const hasValidOnboardingId =
    Number.isInteger(onboardingId) && onboardingId > 0;
  const canUseEventSource = typeof EventSource !== 'undefined';
  const streamUrl =
    hasValidOnboardingId && token ? buildStreamUrl(onboardingId, token) : null;

  useEffect(() => {
    const abortControllers = new Set<AbortController>();
    let isDisposed = false;
    let isProbingError = false;

    const closeEventSource = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };

    const createAbortController = () => {
      const controller = new AbortController();
      abortControllers.add(controller);
      return controller;
    };

    const probeCurrentStream = async () => {
      if (!streamUrl) {
        return 'terminal' satisfies StreamProbeResult;
      }

      const controller = createAbortController();
      try {
        return await probeStreamAvailability(streamUrl, controller.signal);
      } finally {
        abortControllers.delete(controller);
      }
    };

    const inspectStreamError = async () => {
      if (isProbingError) {
        return;
      }

      isProbingError = true;
      try {
        const probeResult = await probeCurrentStream();
        if (isDisposed || probeResult === 'aborted') {
          return;
        }

        if (probeResult === 'terminal') {
          closeEventSource();
          setConnectionStatus({
            onboardingId,
            status: 'unavailable',
          });
          return;
        }

        setConnectionStatus({
          onboardingId,
          status: hasConnectedOnceRef.current ? 'reconnecting' : 'unavailable',
        });
      } finally {
        isProbingError = false;
      }
    };

    const openEventSource = () => {
      if (!streamUrl || isDisposed) {
        return;
      }

      const eventSource = new EventSource(streamUrl, {
        withCredentials: true,
      });

      const handleOpen = () => {
        hasConnectedOnceRef.current = true;
        setConnectionStatus({
          onboardingId,
          status: 'connected',
        });
      };

      const handlePipelineStatus = (event: MessageEvent<string>) => {
        const parsedEvent = parsePipelineStreamEvent(event.data);
        if (!parsedEvent) {
          return;
        }

        setLatestEvent(parsedEvent);
        onEventRef?.current?.(parsedEvent);
        setConnectionStatus({
          onboardingId,
          status: 'connected',
        });
      };

      const handleError = () => {
        if (isDisposed) {
          return;
        }

        setConnectionStatus({
          onboardingId,
          status: hasConnectedOnceRef.current ? 'reconnecting' : 'unavailable',
        });
        void inspectStreamError();
      };

      eventSource.addEventListener('open', handleOpen);
      eventSource.addEventListener(
        'pipeline_status',
        handlePipelineStatus as EventListener,
      );
      eventSource.onerror = handleError;
      eventSourceRef.current = eventSource;

      return () => {
        eventSource.removeEventListener('open', handleOpen);
        eventSource.removeEventListener(
          'pipeline_status',
          handlePipelineStatus as EventListener,
        );
        eventSource.onerror = null;
        eventSource.close();

        if (eventSourceRef.current === eventSource) {
          eventSourceRef.current = null;
        }
      };
    };

    closeEventSource();
    hasConnectedOnceRef.current = false;

    if (!enabled || !hasValidOnboardingId || !canUseEventSource || !streamUrl) {
      return () => {
        isDisposed = true;
        abortControllers.forEach((controller) => controller.abort());
        abortControllers.clear();
        closeEventSource();
      };
    }

    let cleanupEventSource: (() => void) | undefined;

    async function connect() {
      setLatestEvent(null);
      setConnectionStatus({
        onboardingId,
        status: 'connecting',
      });

      const probeResult = await probeCurrentStream();
      if (isDisposed || probeResult === 'aborted') {
        return;
      }

      if (probeResult !== 'ok') {
        setConnectionStatus({
          onboardingId,
          status: 'unavailable',
        });
        return;
      }

      cleanupEventSource = openEventSource();
    }

    void connect();

    return () => {
      isDisposed = true;
      abortControllers.forEach((controller) => controller.abort());
      abortControllers.clear();

      if (cleanupEventSource) {
        cleanupEventSource();
      }

      closeEventSource();
    };
  }, [
    canUseEventSource,
    enabled,
    hasValidOnboardingId,
    onboardingId,
    onEventRef,
    streamUrl,
  ]);

  const resolvedConnectionStatus = !enabled
    ? 'idle'
    : !hasValidOnboardingId || !canUseEventSource || !streamUrl
      ? 'unavailable'
      : connectionStatus.onboardingId === onboardingId
        ? connectionStatus.status
        : 'connecting';
  const resolvedLatestEvent =
    latestEvent?.onboarding_id === onboardingId ? latestEvent : null;

  return {
    connectionStatus: resolvedConnectionStatus,
    latestEvent: resolvedLatestEvent,
  };
}
