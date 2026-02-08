import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../api/client';

export type SSEStatus = 'idle' | 'connecting' | 'connected' | 'error' | 'complete';

export interface UseSSEResult<T> {
    data: T | null;
    status: SSEStatus;
    error: Event | null;
    connect: () => void;
    close: () => void;
    lastMessage: any;
}

export function useSSE<T>(endpoint: string): UseSSEResult<T> {
    const [data, setData] = useState<T | null>(null);
    const [status, setStatus] = useState<SSEStatus>('idle');
    const [error, setError] = useState<Event | null>(null);
    const [lastMessage, setLastMessage] = useState<any>(null);
    const [eventSource, setEventSource] = useState<EventSource | null>(null);

    const connect = useCallback(() => {
        if (eventSource) {
            eventSource.close();
        }

        setStatus('connecting');
        const es = new EventSource(`${API_BASE}${endpoint}`);

        es.onopen = () => {
            setStatus('connected');
            setError(null);
        };

        es.onerror = (e) => {
            console.error('SSE Error:', e);
            setError(e);
            setStatus('error');
            es.close();
        };

        es.addEventListener('progress', (e: MessageEvent) => {
            try {
                const parsed = JSON.parse(e.data);
                setLastMessage(parsed);
                setData(parsed); // Update data with latest progress
            } catch (err) {
                console.error('Failed to parse SSE data', err);
            }
        });

        es.addEventListener('complete', () => {
            setStatus('complete');
            es.close();
        });

        setEventSource(es);
    }, [endpoint]);

    const close = useCallback(() => {
        if (eventSource) {
            eventSource.close();
            setEventSource(null);
            setStatus('idle');
        }
    }, [eventSource]);

    useEffect(() => {
        return () => {
            if (eventSource) {
                eventSource.close();
            }
        };
    }, [eventSource]);

    return { data, status, error, connect, close, lastMessage };
}
