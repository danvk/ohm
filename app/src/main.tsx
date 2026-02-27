import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

(async () => {
  const relationsR = fetch('/static/relations.json');
  const waysR = fetch('/static/ways.json');

  const [relations, ways] = await Promise.all([
    (await relationsR).json(),
    (await waysR).json(),
  ]);

  console.log(
    'Loaded',
    [...Object.keys(relations)].length,
    'relations and',
    [...Object.keys(ways)].length,
    'ways',
  );
})();
