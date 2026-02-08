import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useSSE } from '../hooks/useSSE';

export function SyncControls() {
    const [playlistId, setPlaylistId] = useState('');
    const [isSyncing, setIsSyncing] = useState(false);
    const { status, data, connect } = useSSE('/api/sync/stream');

    const handleSync = async () => {
        if (!playlistId) return;
        try {
            setIsSyncing(true);
            await api.syncPlaylist(playlistId);
            connect();
        } catch (error) {
            console.error('Failed to start sync', error);
            setIsSyncing(false);
        }
    };

    useEffect(() => {
        if (status === 'complete' || status === 'error') {
            setIsSyncing(false);
        }
    }, [status]);

    // Determine progress percentage safely
    const progress = data && typeof data === 'object' && 'progress' in data
        ? (data as any).progress || 0
        : 0;

    return (
        <div className="w-full max-w-md bg-black/40 rounded-xl border border-white/10 p-6 backdrop-blur-md">
            <h3 className="text-xl font-bold mb-4 text-white">Sync Playlist</h3>

            <div className="flex gap-2 mb-4">
                <input
                    type="text"
                    value={playlistId}
                    onChange={(e) => setPlaylistId(e.target.value)}
                    placeholder="Enter Spotify Playlist ID"
                    disabled={isSyncing}
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-[#1DB954] transition-colors"
                />
                <button
                    onClick={handleSync}
                    disabled={isSyncing || !playlistId}
                    className="px-4 py-2 bg-[#1DB954] text-black font-bold rounded-lg hover:bg-[#1ed760] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {isSyncing ? 'Syncing...' : 'Sync'}
                </button>
            </div>

            {/* Progress Bar */}
            {(status === 'connecting' || status === 'connected' || isSyncing) && (
                <div className="space-y-2">
                    <div className="flex justify-between text-xs text-gray-400">
                        <span>{status === 'connecting' ? 'Connecting...' : 'Syncing tracks...'}</span>
                        <span>{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-[#1DB954] transition-all duration-300 ease-out"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    {!!data && (
                        <div className="text-xs text-gray-500 truncate font-mono">
                            {JSON.stringify(data as any)}
                        </div>
                    )}
                </div>
            )}

            {status === 'complete' && (
                <div className="mt-4 p-3 bg-green-500/20 text-green-400 rounded-lg text-sm border border-green-500/30">
                    ✓ Sync complete! Playlist updated.
                </div>
            )}

            {status === 'error' && (
                <div className="mt-4 p-3 bg-red-500/20 text-red-400 rounded-lg text-sm border border-red-500/30">
                    ⚠ Error syncing playlist. Check console.
                </div>
            )}
        </div>
    );
}
