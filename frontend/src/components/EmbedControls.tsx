import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useSSE } from '../hooks/useSSE';

export function EmbedControls() {
    const [isEmbedding, setIsEmbedding] = useState(false);
    const { status, data, connect } = useSSE('/api/embed/stream');

    const handleStartEmbed = async () => {
        try {
            setIsEmbedding(true);
            const res = await api.startEmbed();
            if (res.status === 'started') {
                connect();
            } else {
                alert(res.message || 'Embedding failed to start');
                setIsEmbedding(false);
            }
        } catch (error) {
            console.error('Failed to start embedding', error);
            setIsEmbedding(false);
        }
    };

    useEffect(() => {
        if (status === 'complete' || status === 'error') {
            setIsEmbedding(false);
        }
    }, [status]);

    // Parse progress data
    const progress = data && typeof data === 'object' ? (data as any) : null;
    const current = progress?.current || 0;
    const total = progress?.total || 0;
    const percentage = total > 0 ? (current / total) * 100 : 0;
    const currentSong = progress?.song;

    return (
        <div className="w-full max-w-md bg-black/40 rounded-xl border border-white/10 p-6 backdrop-blur-md">
            <h3 className="text-xl font-bold mb-4 text-white">Generate Embeddings</h3>

            <div className="flex gap-2 mb-4">
                <button
                    onClick={handleStartEmbed}
                    disabled={isEmbedding}
                    className="w-full px-4 py-2 bg-purple-600 text-white font-bold rounded-lg hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {isEmbedding ? 'Generating...' : 'Start Embedding'}
                </button>
            </div>

            {/* Progress Bar */}
            {(status === 'connecting' || status === 'connected' || isEmbedding) && (
                <div className="space-y-4">
                    {/* Overall Progress */}
                    <div className="space-y-1">
                        <div className="flex justify-between text-xs text-gray-400">
                            <span>Overall Progress</span>
                            <span>{current} / {total} songs</span>
                        </div>
                        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-purple-500 transition-all duration-300 ease-out"
                                style={{ width: `${percentage}%` }}
                            />
                        </div>
                    </div>

                    {/* Current Song */}
                    {currentSong && (
                        <div className="p-3 bg-white/5 rounded-lg border border-white/5 animate-pulse">
                            <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">Processing Now</div>
                            <div className="text-sm font-medium text-white truncate">{currentSong.title}</div>
                            <div className="text-xs text-gray-400 truncate">{currentSong.artist}</div>
                        </div>
                    )}
                </div>
            )}

            {status === 'complete' && (
                <div className="mt-4 p-3 bg-green-500/20 text-green-400 rounded-lg text-sm border border-green-500/30">
                    ✓ Embeddings generated!
                </div>
            )}

            {status === 'error' && (
                <div className="mt-4 p-3 bg-red-500/20 text-red-400 rounded-lg text-sm border border-red-500/30">
                    ⚠ Error generating embeddings. Check console.
                </div>
            )}
        </div>
    );
}
