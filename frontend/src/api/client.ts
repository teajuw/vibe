export const API_BASE = 'http://localhost:8000';

export interface SyncResponse {
    status: string;
}

export interface AuthUrlResponse {
    url: string;
}

export interface LibraryResponse {
    songs: any[]; // refine type later
    stats: {
        total: number;
        downloaded: number;
        embedded: number;
    };
}

export const api = {
    getAuthUrl: async (): Promise<string> => {
        const res = await fetch(`${API_BASE}/api/auth/url`);
        const data: AuthUrlResponse = await res.json();
        return data.url;
    },

    checkAuth: async (): Promise<boolean> => {
        try {
            const res = await fetch(`${API_BASE}/api/auth/status`);
            const data = await res.json();
            return data.authenticated;
        } catch (e) {
            return false;
        }
    },

    handleCallback: async (code: string): Promise<void> => {
        await fetch(`${API_BASE}/api/auth/callback?code=${code}`);
    },

    syncPlaylist: async (playlistId: string): Promise<SyncResponse> => {
        const res = await fetch(`${API_BASE}/api/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ playlist_id: playlistId }),
        });
        return res.json();
    },

    startDownload: async (): Promise<{ status: string; total: number; message?: string }> => {
        const res = await fetch(`${API_BASE}/api/download`, {
            method: 'POST',
        });
        return res.json();
    },

    getLibrary: async (): Promise<LibraryResponse> => {
        const res = await fetch(`${API_BASE}/api/library`);
        return res.json();
    }
};
