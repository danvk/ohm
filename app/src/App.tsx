import React from 'react';
import { MapLibreMap } from './MapLibreMap';

const DEFAULT_CENTER: [number, number] = [0, 20];

export default function App() {
  return (<div style={{ width: '100vw', height: '100vh' }}>
    <MapLibreMap center={DEFAULT_CENTER} zoom={1.5} />
  </div>);
}
