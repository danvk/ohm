import React, {
  useEffect,
  useRef,
  useState,
  createContext,
  useContext,
} from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MINIMAL_STYLE } from './map-style';

export interface MapView {
  zoom: number;
  lat: number;
  lng: number;
}

interface MapLibreMapProps extends Partial<maplibregl.MapOptions> {
  containerId?: string;
  containerClassName?: string;
  onClick?: () => void;
  onMapMove?: (view: MapView) => void;
  /** When set, imperatively flies the map to this view. Use a new object reference to trigger. */
  externalView?: MapView & { seq: number };
  children?: React.JSX.Element | React.JSX.Element[];
}

const MapContext = createContext<maplibregl.Map | undefined>(undefined);

export function useMap() {
  return useContext(MapContext);
}

export function MapLibreMap({
  children,
  onClick,
  onMapMove,
  externalView,
  containerId,
  containerClassName,
  ...mapOptions
}: MapLibreMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [mapRef, setMapRef] = useState<maplibregl.Map | undefined>();
  const [initialOptions] = useState<typeof mapOptions>(mapOptions);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: MINIMAL_STYLE,
      dragRotate: false,
      rollEnabled: false,
      pitchWithRotate: false,
      ...initialOptions,
    });
    map.on('style.load', () => {
      // It's dangerous to interact with the map before the style is done loading.
      setMapRef(map);
    });

    return () => {
      map.remove();
    };
  }, [initialOptions]);

  // Imperatively reposition the map when an external navigation arrives.
  React.useEffect(() => {
    if (!mapRef || !externalView) return;
    mapRef.setCenter([externalView.lng, externalView.lat]);
    mapRef.setZoom(externalView.zoom);
  }, [mapRef, externalView]);

  React.useEffect(() => {
    if (onClick) {
      mapRef?.on('click', onClick);
      return () => {
        mapRef?.off('click', onClick);
      };
    }
  }, [mapRef, onClick]);

  const onMapMoveRef = React.useRef(onMapMove);
  React.useEffect(() => {
    onMapMoveRef.current = onMapMove;
  }, [onMapMove]);

  React.useEffect(() => {
    if (!mapRef) return;
    const handler = () => {
      const { lng, lat } = mapRef.getCenter();
      onMapMoveRef.current?.({ zoom: mapRef.getZoom(), lat, lng });
    };
    mapRef.on('moveend', handler);
    return () => void mapRef.off('moveend', handler);
  }, [mapRef]);

  // TODO: maybe another wrapper div would be safer -- setting containerClassName here is dangerous.
  return (
    <>
      <div
        ref={mapContainerRef}
        id={containerId}
        className={containerClassName}
      />
      <MapContext.Provider value={mapRef}>{children}</MapContext.Provider>
    </>
  );
}
