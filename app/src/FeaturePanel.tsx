import React from 'react';

export interface FeatureInfo {
  id: string | number;
  tags: Record<string, string>;
  chronology?: Chronology[];
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
  onSelectRelation: (relationId: number) => void;
  onClose: () => void;
}

export function FeaturePanel({
  features,
  onClose,
  onSetYear,
  onSelectRelation,
}: FeaturePanelProps) {
  if (features.length === 0) return null;

  return (
    <div id="feature-panel">
      <button id="feature-panel-close" onClick={onClose}>
        ✕
      </button>
      {features.map((f) => (
        <FeatureInfo
          key={f.id}
          feature={f}
          onSetYear={onSetYear}
          onSelectRelation={onSelectRelation}
        />
      ))}
    </div>
  );
}

function FeatureInfo({
  feature,
  onSetYear,
  onSelectRelation,
}: {
  feature: FeatureInfo;
  onSetYear: FeaturePanelProps['onSetYear'];
  onSelectRelation: FeaturePanelProps['onSelectRelation'];
}) {
  const { id, tags, chronology } = feature;
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
      {chronology && chronology.length > 0 && (
        <div className="chronologies">
          {chronology.map((c) => (
            <ChronologyRow
              key={c.id}
              entry={c}
              onSelectRelation={onSelectRelation}
            />
          ))}
        </div>
      )}
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

function ChronologyRow({
  entry,
  onSelectRelation,
}: {
  entry: Chronology;
  onSelectRelation: FeaturePanelProps['onSelectRelation'];
}) {
  return (
    <div className="chronology-row">
      {entry.prev !== undefined ? (
        <a
          href="#"
          title="Previous in chronology"
          onClick={(e) => {
            e.preventDefault();
            onSelectRelation(entry.prev!);
          }}
        >
          ←
        </a>
      ) : (
        <span className="chronology-arrow-placeholder" />
      )}
      <a
        href={`https://www.openhistoricalmap.org/relation/${entry.id}`}
        target="_blank"
        className="chronology-name"
      >
        {entry.name}
      </a>
      {entry.next !== undefined ? (
        <a
          href="#"
          title="Next in chronology"
          onClick={(e) => {
            e.preventDefault();
            onSelectRelation(entry.next!);
          }}
        >
          →
        </a>
      ) : (
        <span className="chronology-arrow-placeholder" />
      )}
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
