import React from 'react';
import { useMap } from './MapLibreMap';
import maplibregl from 'maplibre-gl';

export function ZoomControl() {
  const map = useMap();
  React.useEffect(() => {
    let control: maplibregl.IControl;
    if (map) {
      control = new maplibregl.NavigationControl({
        showZoom: true,
        showCompass: false,
      });
      map.addControl(control, 'top-left');
    }
    return () => {
      // console.log('destroy controls', map, control)
      if (map && control) {
        map.removeControl(control);
      }
    };
  }, [map]);
  return null;
}
