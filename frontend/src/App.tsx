import { useState, useEffect } from 'react';
import { api } from './api/client';
import { ConnectSpotify } from './components/ConnectSpotify';
import { SyncControls } from './components/SyncControls';
import { DownloadControls } from './components/DownloadControls';
import { EmbedControls } from './components/EmbedControls';
import { SearchInterface } from './components/SearchInterface';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const init = async () => {
      // Check for auth code in URL
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');

      if (code) {
        try {
          // Clear code from URL to prevent re-submission
          window.history.replaceState({}, '', '/');
          await api.handleCallback(code);
          setIsAuthenticated(true);
        } catch (e) {
          console.error('Auth callback failed', e);
        }
      } else {
        // Check current status
        const auth = await api.checkAuth();
        setIsAuthenticated(auth);
      }
      setLoading(false);
    };

    init();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-pulse text-green-500 font-bold text-xl">
          Vibe Search...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-8 font-sans selection:bg-green-500/30">
      <header className="max-w-4xl mx-auto mb-12 flex items-center justify-between">
        <h1 className="text-4xl font-black tracking-tighter bg-gradient-to-br from-green-400 to-blue-500 bg-clip-text text-transparent">
          Vibe Search
        </h1>
        <div className="text-xs font-mono text-gray-500 border border-gray-800 px-3 py-1 rounded-full">
          v0.1.0-alpha
        </div>
      </header>

      <main className="max-w-4xl mx-auto space-y-8">
        {!isAuthenticated ? (
          <div className="flex flex-col items-center justify-center min-h-[400px]">
            <ConnectSpotify />
          </div>
        ) : (
          <div className="space-y-12">
            <section>
              <SearchInterface />
            </section>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-8 border-t border-white/10">
              <section>
                <h2 className="text-2xl font-bold mb-4 text-gray-200">Library Sync</h2>
                <SyncControls />
              </section>

              <section className="bg-gray-900/50 rounded-xl p-6 border border-white/5">
                <h2 className="text-xl font-bold mb-4 text-gray-400">Pipeline Status</h2>
                <div className="space-y-4">
                  <div className="flex items-center gap-3 text-sm text-gray-500">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    System Online
                  </div>

                  <DownloadControls />
                  <EmbedControls />

                  {/* Placeholder for future pipeline steps */}
                  <div className="p-4 bg-black/40 rounded-lg border border-white/5">
                    <div className="text-xs uppercase tracking-widest text-gray-600 mb-2">Next Steps</div>
                    <ul className="space-y-2 text-sm text-gray-400">
                      <li className="flex items-center gap-2 opacity-50">
                        <span className="w-4 h-4 rounded-full border border-gray-600 flex items-center justify-center text-[10px]">1</span>
                        Download Audio
                      </li>
                      <li className="flex items-center gap-2 opacity-50">
                        <span className="w-4 h-4 rounded-full border border-gray-600 flex items-center justify-center text-[10px]">2</span>
                        Generate Embeddings
                      </li>
                    </ul>
                  </div>
                </div>
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
