import { useState } from 'react';
import UploadScreen from './screens/UploadScreen.tsx';
import AskScreen from './screens/AskScreen.tsx';
import DocumentsScreen from './screens/DocumentsScreen.tsx';

type Screen = 'upload' | 'ask' | 'documents';

function App() {
  const [screen, setScreen] = useState<Screen>('upload');

  return (
    <div>
      <nav>
        <a
          href="#"
          className={screen === 'upload' ? 'active' : ''}
          onClick={(e) => {
            e.preventDefault();
            setScreen('upload');
          }}
        >
          Upload Document
        </a>
        <a
          href="#"
          className={screen === 'ask' ? 'active' : ''}
          onClick={(e) => {
            e.preventDefault();
            setScreen('ask');
          }}
        >
          Ask a Question
        </a>
        <a
          href="#"
          className={screen === 'documents' ? 'active' : ''}
          onClick={(e) => {
            e.preventDefault();
            setScreen('documents');
          }}
        >
          Approved Documents
        </a>
      </nav>

      {screen === 'upload' && <UploadScreen />}
      {screen === 'ask' && <AskScreen />}
      {screen === 'documents' && <DocumentsScreen />}
    </div>
  );
}

export default App;