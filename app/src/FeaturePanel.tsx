import React from 'react';

export interface FeatureInfo {
  id: string | number;
  tags: Record<string, string>;
}

const SHOWN_TAGS = [
  'name',
  'name:en',
  'start_date',
  'end_date',
  'admin_level',
  'boundary',
  'type',
  'place',
  'wikidata',
  'wikipedia',
] as const;

export interface FeaturePanelProps {
  features: FeatureInfo[];
  onClose: () => void;
}

export function FeaturePanel({ features, onClose }: FeaturePanelProps) {
  if (features.length === 0) return null;

  return (
    <div id="feature-panel">
      <button id="feature-panel-close" onClick={onClose}>
        ✕
      </button>
      {features.map((f) => (
        <div key={f.id} className="feature-info">
          <h3>OSM relation {f.id}</h3>
          <table>
            <tbody>
              {SHOWN_TAGS.filter((tag) => tag in f.tags).map((tag) => (
                <tr key={tag}>
                  <th>{tag}</th>
                  <td>{f.tags[tag]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
