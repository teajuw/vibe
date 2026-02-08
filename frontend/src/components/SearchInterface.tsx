import { useState } from 'react';
import { api } from '../api/client';
import type { SearchResponse } from '../api/client';

export function SearchInterface() {
    const [query, setQuery] = useState('');
    const [isSearching, setIsSearching] = useState(false);
    const [results, setResults] = useState<SearchResponse['results']>([]);
    const [hasSearched, setHasSearched] = useState(false);

    const handleSearch = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!query.trim()) return;

        try {
            setIsSearching(true);
            const res = await api.search(query);
            setResults(res.results);
            setHasSearched(true);
        } catch (error) {
            console.error('Search failed', error);
            alert('Search failed');
        } finally {
            setIsSearching(false);
        }
    };

    return (
        <div className="w-full max-w-4xl mx-auto space-y-8">
            {/* Search Input */}
            <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-green-400 to-blue-500 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
                <form onSubmit={handleSearch} className="relative flex gap-2 p-2 bg-black rounded-xl ring-1 ring-white/10">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Describe the vibe (e.g., 'driving deeply into the night')"
                        className="flex-1 bg-transparent text-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none"
                        autoFocus
                    />
                    <button
                        type="submit"
                        disabled={isSearching || !query.trim()}
                        className="px-8 py-3 bg-white text-black font-bold rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-95"
                    >
                        {isSearching ? 'Vibing...' : 'Vibe Check'}
                    </button>
                </form>
            </div>

            {/* Results */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {results.map((track) => (
                    <a
                        key={track.spotify_id}
                        href={track.spotify_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group flex gap-4 p-4 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 hover:border-white/20 transition-all hover:-translate-y-1"
                    >
                        <img
                            src={track.album_art_url}
                            alt={track.album}
                            className="w-20 h-20 rounded-lg shadow-lg group-hover:shadow-2xl transition-shadow"
                        />
                        <div className="flex-1 min-w-0">
                            <h4 className="font-bold text-white truncate text-lg">{track.title}</h4>
                            <p className="text-gray-400 truncate">{track.artist}</p>
                            <p className="text-xs text-gray-600 truncate mb-2">{track.album}</p>

                            <div className="flex items-center gap-2">
                                <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-green-400 to-blue-500"
                                        style={{ width: `${track.similarity_score * 100}%` }}
                                    />
                                </div>
                                <span className="text-xs font-mono text-green-400">
                                    {Math.round(track.similarity_score * 100)}%
                                </span>
                            </div>
                        </div>
                    </a>
                ))}
            </div>

            {hasSearched && results.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                    <div className="text-4xl mb-4">🤷‍♂️</div>
                    <p>No vibes found. Try syncing more songs!</p>
                </div>
            )}
        </div>
    );
}
