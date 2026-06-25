import { useState, useCallback } from 'react';
import { askQuestion, searchDocuments } from '../api';
import type { AskResponse, SearchResponse, SearchResult } from '../types';

export default function AskScreen() {
  const [query, setQuery] = useState('');
  const [discipline, setDiscipline] = useState('');
  const [mode, setMode] = useState<'qa' | 'search'>('qa');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qaResult, setQaResult] = useState<AskResponse | null>(null);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim()) {
        setError('Please enter a question or search query.');
        return;
      }

      setLoading(true);
      setError(null);
      setQaResult(null);
      setSearchResult(null);

      try {
        if (mode === 'qa') {
          const result = (await askQuestion({
            query: query.trim(),
            discipline: discipline || undefined,
          })) as AskResponse;
          setQaResult(result);
        } else {
          const result = (await searchDocuments({
            query: query.trim(),
            limit: 10,
            discipline: discipline || undefined,
          })) as SearchResponse;
          setSearchResult(result);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Request failed');
      } finally {
        setLoading(false);
      }
    },
    [query, discipline, mode]
  );

  return (
    <div>
      <h2>Ask a Question</h2>

      <div style={{ marginBottom: '1rem' }}>
        <label>
          <input
            type="radio"
            checked={mode === 'qa'}
            onChange={() => setMode('qa')}
          />{' '}
          Q&A
        </label>
        <label style={{ marginLeft: '1rem' }}>
          <input
            type="radio"
            checked={mode === 'search'}
            onChange={() => setMode('search')}
          />{' '}
          Search
        </label>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="query">Query</label>
          <br />
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
            style={{ width: '100%' }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="discipline">Discipline (optional)</label>
          <br />
          <select
            id="discipline"
            value={discipline}
            onChange={(e) => setDiscipline(e.target.value)}
          >
            <option value="">-- All disciplines --</option>
            <option value="ELC">ELC</option>
            <option value="MEC">MEC</option>
            <option value="INS">INS</option>
            <option value="SIM">SIM</option>
          </select>
        </div>

        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? 'Working...' : mode === 'qa' ? 'Ask' : 'Search'}
        </button>
      </form>

      {error && (
        <p style={{ color: 'red', marginTop: '1rem' }}>
          Error: {error}
        </p>
      )}

      {qaResult && (
        <div style={{ marginTop: '1rem' }}>
          <h3>Answer</h3>
          <p>{qaResult.answer}</p>
          <p>
            <strong>Confidence:</strong> {qaResult.confidence}
          </p>
          <p>
            <strong>Context chunks used:</strong> {qaResult.context_chunks_used}
          </p>

          {qaResult.citations.length > 0 && (
            <>
              <h4>Citations</h4>
              <ul>
                {qaResult.citations.map((citation, index) => (
                  <li key={index}>
                    <strong>{citation.document_number}</strong>
                    {citation.title && <> - {citation.title}</>}
                    <br />
                    <em>{citation.page_or_sheet}</em>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {searchResult && (
        <div style={{ marginTop: '1rem' }}>
          <h3>Search Results</h3>
          <p>
            <strong>Total:</strong> {searchResult.total}
          </p>
          {searchResult.results.map((result: SearchResult) => (
            <div
              key={result.chunk_id}
              style={{
                border: '1px solid #e2e8f0',
                borderRadius: '0.5rem',
                padding: '1rem',
                marginBottom: '0.5rem',
              }}
            >
              <p style={{ margin: 0 }}>
                <strong>Score:</strong> {result.score.toFixed(3)}
              </p>
              <p style={{ margin: '0.5rem 0 0' }}>{result.content}</p>
              <p style={{ margin: '0.5rem 0 0', fontSize: '0.875rem', color: '#64748b' }}>
                Document: {result.document_number ?? result.document_id}
                {result.discipline && <> | Discipline: {result.discipline}</>}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}