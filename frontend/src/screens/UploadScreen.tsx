import { useState, useCallback, useRef, useEffect } from 'react';
import { uploadDocument, getUploadStatus } from '../api';
import type { UploadResponse, StatusResponse } from '../types';

export default function UploadScreen() {
  const [file, setFile] = useState<File | null>(null);
  const [discipline, setDiscipline] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setUploadResult(null);
    setStatus(null);
    setError(null);
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!file) {
        setError('Please select a file to upload.');
        return;
      }

      // Clear any existing polling
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }

      setUploading(true);
      setError(null);
      setUploadResult(null);
      setStatus(null);

      try {
        console.log('Uploading file:', file.name);
        const result = (await uploadDocument(file, discipline || undefined)) as UploadResponse;
        console.log('Upload result:', result);
        setUploadResult(result);

        // Start polling for status updates
        pollIntervalRef.current = window.setInterval(async () => {
          try {
            console.log('Polling status for job:', result.job_id);
            const statusUpdate = (await getUploadStatus(result.job_id)) as StatusResponse;
            console.log('Status update:', statusUpdate);
            setStatus(statusUpdate);

            // Stop polling if job is complete
            if (statusUpdate.status === 'Approved' || statusUpdate.status === 'Rejected') {
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
              }
              console.log('Polling stopped - job complete');
            }
          } catch (err) {
            console.error('Polling error:', err);
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
          }
        }, 2000); // Poll every 2 seconds
      } catch (err) {
        console.error('Upload error:', err);
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [file, discipline]
  );

  return (
    <div>
      <h2>Upload Document</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="file">File</label>
          <br />
          <input
            id="file"
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.dwg,.dxf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.tif,.tiff"
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
            <option value="">-- Select discipline --</option>
            <option value="ELC">ELC</option>
            <option value="MEC">MEC</option>
            <option value="INS">INS</option>
            <option value="SIM">SIM</option>
          </select>
        </div>

        <button type="submit" disabled={uploading || !file}>
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>

      {error && (
        <p style={{ color: 'red', marginTop: '1rem' }}>
          Error: {error}
        </p>
      )}

      {uploadResult && (
        <div style={{ marginTop: '1rem' }}>
          <p>
            <strong>Uploaded:</strong> {uploadResult.filename}
          </p>
          <p>
            <strong>Job ID:</strong> {uploadResult.job_id}
          </p>
          <p>
            <strong>Status:</strong> {uploadResult.status}
          </p>
          <p>{uploadResult.message}</p>
        </div>
      )}

      {status && (
        <div style={{ marginTop: '1rem' }}>
          <p>
            <strong>Current Status:</strong> {status.status}
          </p>
          <p>
            <strong>Progress:</strong> {status.progress}%
          </p>
          <p>
            <strong>Updated:</strong>{' '}
            {new Date(status.updated_at).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  );
}