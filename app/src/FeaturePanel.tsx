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
  onSetYear: (year: number) => void;
  onClose: () => void;
}

export function FeaturePanel({
  features,
  onClose,
  onSetYear,
}: FeaturePanelProps) {
  if (features.length === 0) return null;

  return (
    <div id="feature-panel">
      <button id="feature-panel-close" onClick={onClose}>
        ✕
      </button>
      {features.map((f) => (
        <FeatureInfo key={f.id} feature={f} onSetYear={onSetYear} />
      ))}
    </div>
  );
}

function FeatureInfo({
  feature,
  onSetYear,
}: {
  feature: FeatureInfo;
  onSetYear: FeaturePanelProps['onSetYear'];
}) {
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
              <th title={key}>{key}</th>
              <td>
                <TagValue tagKey={key} value={value} onSetYear={onSetYear} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TagValue({
  tagKey,
  value,
  onSetYear,
}: {
  tagKey: string;
  value: string;
  onSetYear: FeaturePanelProps['onSetYear'];
}) {
  if (tagKey === 'wikipedia') {
    const [lang] = value.split(':', 1);
    const url = `https://${lang}.wikipedia.org/wiki/${value}`;
    return (
      <a href={url} target="_blank">
        {value}
      </a>
    );
  }
  if ((tagKey === 'start_date' || tagKey === 'end_date') && value) {
    const year = Number(value.slice(0, 4));
    return (
      <a
        href="#"
        onClick={(e) => {
          e.preventDefault();
          onSetYear(year);
        }}
      >
        {value}
      </a>
    );
  }
  if (value.startsWith('https://')) {
    return (
      <a href={value} target="_blank">
        (link)
      </a>
    );
  }
  return value;
}
