import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { NuqsAdapter } from 'nuqs/adapters/react-router/v7';
import App from './App.tsx';
import './app.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <NuqsAdapter>
        <App />
      </NuqsAdapter>
    </BrowserRouter>
  </React.StrictMode>,
);
