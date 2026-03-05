import { useEffect, useMemo, useState } from 'react';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const canSearch = query.trim().length > 3;

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length <= 3) {
      setResults([]);
      setError('');
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(async () => {
      try {
        setLoading(true);
        setError('');
        const url = new URL(`${API_BASE_URL}/search`);
        url.searchParams.set('q', trimmed);
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const payload = await response.json();
        setResults(Array.isArray(payload.results) ? payload.results : []);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(`Could not fetch matches from backend at ${API_BASE_URL}`);
          setResults([]);
        }
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => {
      controller.abort();
      clearTimeout(timeoutId);
    };
  }, [query]);

  const tableRows = useMemo(() => {
    return results.map((item, idx) => ({
      rank: idx + 1,
      match: item.display,
      final_score: item.final_score,
      ratio_score: item.ratio_score,
      token_sort_score: item.token_sort_score,
      token_set_score: item.token_set_score,
      token_coverage: item.token_coverage,
      coverage_boost: item.coverage_boost,
      number_penalty: item.number_penalty,
    }));
  }, [results]);

  return (
    <div className="page">
      <main className="content">
        <h1 className="logo">FindCare</h1>

        <div className="search-shell">
          <input
            className="search-input"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search filters (type at least 4 characters)"
            aria-label="Search filters"
          />
        </div>

        {loading && <p className="status">Searching...</p>}
        {!loading && !canSearch && <p className="status">Start typing. Search begins after 3 characters.</p>}
        {!loading && canSearch && !error && results.length === 0 && <p className="status">No matching options found.</p>}
        {error && <p className="error">{error}</p>}

        {results.length > 0 && (
          <section className="results-card" aria-label="Search suggestions">
            <ul className="results-list">
              {results.map((item) => (
                <li className="result-item" key={`${item.source}-${item.value}`}>
                  <span className="result-title">{item.value}</span>
                  <span className="result-source">{item.source}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {tableRows.length > 0 && (
          <section className="table-section" aria-label="Score breakdown table">
            <h2 className="table-title">Score Breakdown</h2>
            <div className="table-scroll">
              <table className="scores-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Match</th>
                    <th>Final</th>
                    <th>Ratio</th>
                    <th>Token Sort</th>
                    <th>Token Set</th>
                    <th>Coverage</th>
                    <th>Boost</th>
                    <th>Penalty</th>
                  </tr>
                </thead>
                <tbody>
                  {tableRows.map((row) => (
                    <tr key={row.rank}>
                      <td>{row.rank}</td>
                      <td>{row.match}</td>
                      <td>{row.final_score}</td>
                      <td>{row.ratio_score}</td>
                      <td>{row.token_sort_score}</td>
                      <td>{row.token_set_score}</td>
                      <td>{row.token_coverage}</td>
                      <td>{row.coverage_boost}</td>
                      <td>{row.number_penalty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
