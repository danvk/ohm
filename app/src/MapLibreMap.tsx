import React, {
  useEffect,
  useRef,
  useState,
  createContext,
  useContext,
} from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const MINIMAL_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    maplibre: {
      type: 'vector',
      url: 'https://demotiles.maplibre.org/tiles/tiles.json',
    },
  },
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: { 'background-color': '#e8e8e8' },
    },
    {
      id: 'countries-fill',
      type: 'fill',
      source: 'maplibre',
      'source-layer': 'countries',
      paint: { 'fill-color': '#aaaaaa' },
    },
  ],
};

interface MapLibreMapProps extends Partial<maplibregl.MapOptions> {
  containerId?: string;
  containerClassName?: string;
  onClick?: () => void;
  children?: React.JSX.Element | React.JSX.Element[];
}

const MapContext = createContext<maplibregl.Map | undefined>(undefined);

export function useMap() {
  return useContext(MapContext);
}

export function MapLibreMap({
  children,
  onClick,
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

  // TODO: other options should be reactive, too
  const { center } = mapOptions;
  React.useEffect(() => {
    if (center) {
      mapRef?.setCenter(center);
    }
  }, [center, mapRef]);

  React.useEffect(() => {
    if (onClick) {
      mapRef?.on('click', onClick);
      return () => {
        mapRef?.off('click', onClick);
      };
    }
  }, [mapRef, onClick]);

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
