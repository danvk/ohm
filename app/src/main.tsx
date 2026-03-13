import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './app.css';
import type { AppData } from './loader.ts';
import { loadData } from './loader.ts';

/** Wraps a Promise into the "suspense resource" pattern. */
function createResource<T>(promise: Promise<T>) {
  let status: 'pending' | 'success' | 'error' = 'pending';
  let result: T;
  let error: unknown;
  const suspender = promise.then(
    (data) => {
      status = 'success';
      result = data;
    },
    (err) => {
      status = 'error';
      error = err;
    },
  );
  return {
    read(): T {
      if (status === 'pending') throw suspender;
      if (status === 'error') throw error;
      return result;
    },
  };
}

const dataResource = createResource<AppData>(loadData());

function AppWithData() {
  const data = dataResource.read();
  return <App data={data} />;
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <React.Suspense fallback={<div className="loading">Loading data…</div>}>
      <AppWithData />
    </React.Suspense>
  </React.StrictMode>,
);
