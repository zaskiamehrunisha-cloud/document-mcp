import { useState, useEffect, useCallback } from 'react';
import { getDocuments } from '../api';
import type { DocumentListResponse, DocumentResponse } from '../types';

export default function DocumentsScreen() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = (await getDocuments(page, pageSize)) as DocumentListResponse;
      setDocuments(result.documents);
      setTotal(result.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <h2>Approved Documents</h2>

      {error && (
        <p style={{ color: 'red', marginTop: '1rem' }}>
          Error: {error}
        </p>
      )}

      {loading && documents.length === 0 && <p>Loading documents...</p>}

      {!loading && documents.length === 0 && (
        <p>No approved documents found.</p>
      )}

      {documents.length > 0 && (
        <>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              marginTop: '1rem',
            }}
          >
            <thead>
              <tr>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>ID</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>Document Number</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>Title</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>Discipline</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>Status</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>Updated</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td style={{ borderBottom: '1px solid #e2e8f0' }}>{doc.id}</td>
                  <td style={{ borderBottom: '1px solid #e2e8f0' }}>{doc.document_number ?? '-'}</td>
                  <td style={{ borderBottom: '1px solid #e2e8f0' }}>{doc.title ?? '-'}</td>
                  <td style={{ borderBottom: '1px solid #e2e8f0' }}>{doc.discipline ?? '-'}</td>
                  <td style={{ borderBottom: '1px solid #e2e8f0' }}>{doc.status}</td>
                  <td style={{ borderBottom: '1px solid #e2e8f0' }}>
                    {new Date(doc.updated_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span>
              Page {page} of {totalPages || 1}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}