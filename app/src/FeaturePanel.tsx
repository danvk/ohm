import React from 'react';

export interface FeatureInfo {
  id: string | number;
  tags: Record<string, string>;
}

const EXACT_TAGS = [
  'name',
  'name:en',
  'admin_level',
  'boundary',
  'type',
  'place',
  'disputed',
  'wikidata',
  'wikipedia',
];
const PREFIX_TAGS = [
  'start_date',
  'end_date',
  'start_event',
  'end_event',
  'source',
  'note',
  'fixme',
];
const EXACT_RE = EXACT_TAGS.join('|');
const PREFIX_RE = PREFIX_TAGS.join('|');
const KEY_PAT = new RegExp(`^(?:(?:(?:${EXACT_RE})$)|(?:${PREFIX_RE}))`);

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
              {Object.entries(f.tags)
                .filter(([key]) => KEY_PAT.exec(key))
                .map(([key, value]) => (
                  <tr key={key}>
                    <th>{key}</th>
                    <td>{value}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
