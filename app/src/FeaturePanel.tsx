import React from 'react';

export interface FeatureInfo {
  id: string | number;
  tags: Record<string, string>;
}

const EXACT_TAGS = [
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
        <FeatureInfo key={f.id} feature={f} />
      ))}
    </div>
  );
}

function FeatureInfo({ feature }: { feature: FeatureInfo }) {
  const { id, tags } = feature;
  const tagsToShow = Object.entries(tags).filter(([key]) => KEY_PAT.exec(key));
  const name = tags['name:en'] ?? tags['name'];

  return (
    <div className="feature-info">
      <h3>
        <a
          href={`https://www.openhistoricalmap.org/relation/${id}`}
          target="_blank"
        >
          {name}
        </a>
      </h3>
      <table>
        <tbody>
          {tagsToShow.map(([key, value]) => (
            <tr key={key}>
              <th>{key}</th>
              <td>
                <TagValue tagKey={key} value={value} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TagValue({ tagKey, value }: { tagKey: string; value: string }) {
  if (tagKey === 'wikipedia') {
    const [lang] = value.split(':', 1);
    const url = `https://${lang}.wikipedia.org/wiki/${value}`;
    return (
      <a href={url} target="_blank">
        {value}
      </a>
    );
  }
  return value;
}
