/** Base URL for the dashboard data server. */
export const SERVER = "https://s3.amazonaws.com/planet.openhistoricalmap.org/planet-stats";

// "http://localhost:8081";

/**
 * Per-metric documentation used in chart legends.
 *
 * `label` is a short display name; `help` is shown as a tooltip.
 */
export const METRIC_DOCS = {
  date: { label: "Date", help: "Date of planet dump file" },
  "nonclosed-ring": {
    label: "Non-closed Rings",
    help: "At least one ring (inner or outer) in the relation could not be closed. It's likely that a way is missing.",
  },
  "ring-self-intersect": {
    label: "Ring Self-intersects",
    help: "At least one ring (inner or outer) in the relation intersects itself.",
  },
  "self-intersect": {
    label: "Self-intersects",
    help: "Two rings in the relation cross each other.",
  },
  "uncontained-inner-ring": {
    label: "Uncontained inner",
    help: "A role=inner ring is not contained in any outer ring.",
  },
  "nested-shells": {
    label: "Nested Rings",
    help: "One ring is contained inside another without role=inner.",
  },
  "no-shapely": {
    label: "Shapely Error",
    help: "Shapely was unable to create a geometry for this relation.",
  },
  other: { label: "Other", help: "A grab bag of all other geometry errors." },
  "invalid-way-reference": {
    label: "Invalid Way Reference",
    help: "A relation member references a way that does not exist in the data.",
  },

  "chronology-member-outside-range": {
    label: "Member Outside Parent Range",
    help: "The chronology itself has start_date/end_date, but one of its members has a date range outside of that.",
  },
  "chronology-overlapping-members": {
    label: "Overlapping Members",
    help: "Two members of the chronology have overlapping date ranges. One of them likely needs to be adjusted.",
  },
  "chronology-undated-member": {
    label: "Undated Members",
    help: "Chronologies that contain undated members (no start_date or end_date).",
  },

  "date-in-name": {
    label: "Date Ranges in name",
    help: "The feature's name tag contains a date range.",
  },
  "date-invalid": {
    label: "Invalid Dates",
    help: "Either start_date or end_date cannot be parsed as ISO.",
  },
  "date-end-no-start": {
    label: "end_date w/o start_date",
    help: "If a feature has end_date, then it should have start_date. Nothing is timeless.",
  },
  "date-start-after-end": {
    label: "start_date > end_date",
    help: "The feature has a valid start_date and end_date, but start_date > end_date.",
  },
  "date-far-future": {
    label: "Far future",
    help: "Either start_date or end_date is after 2050. This is often a typo or placeholder, but omitting end_date is preferable.",
  },
  "date-edtf-invalid": {
    label: "Invalid EDTF date",
    help: "Features with start_date:edtf or end_date:edtf that cannot be parsed as EDTF.",
  },
  "date-edtf-mismatch": {
    label: "Mismatched EDTF date",
    help: "A feature specifies both start_date and start_date:edtf (or end_date/end_date:edtf), but the two do not overlap.",
  },

  "earth-years-admin-1": { label: "admin1", help: "See above for an explanation of this metric." },
  "earth-years-admin-2": { label: "admin2", help: "See above for an explanation of this metric." },
  "earth-years-admin-3": { label: "admin3", help: "See above for an explanation of this metric." },
  "earth-years-admin-4": { label: "admin4", help: "See above for an explanation of this metric." },

  "double-covered-admin-1": { label: "admin1", help: "" },
  "double-covered-admin-2": { label: "admin2", help: "" },
  "double-covered-admin-3": { label: "admin3", help: "" },
  "double-covered-admin-4": { label: "admin4", help: "" },

  "num-nodes": { label: "Nodes" },
  "num-ways": { label: "Ways" },
  "num-relations": { label: "Relations" },
  dupes: {
    label: "Duplicate Relations",
    help:
      "Number of relations that have a likely duplicate. " +
      "Each set of likely duplicates counts once.",
  },
};

/**
 * Metric groupings used to populate the diff-page dropdown.
 *
 * Labels here are more descriptive than in METRIC_DOCS because the dropdown
 * lacks the chart-section headings that provide context on the main page.
 */
export const METRIC_GROUPS = [
  {
    label: "Geometry Errors",
    metrics: [
      "nonclosed-ring",
      "ring-self-intersect",
      "self-intersect",
      "uncontained-inner-ring",
      "nested-shells",
      "no-shapely",
      "other",
      "invalid-way-reference",
    ],
  },
  {
    label: "Chronology Errors",
    metrics: [
      "chronology-member-outside-range",
      "chronology-overlapping-members",
      "chronology-undated-member",
    ],
  },
  {
    label: "Tag Errors",
    metrics: [
      "date-in-name",
      "date-invalid",
      "date-end-no-start",
      "date-far-future",
      "date-start-after-end",
      "date-edtf-invalid",
      "date-edtf-mismatch",
    ],
  },
  {
    label: "Coverage",
    metrics: [
      "earth-years-admin-1",
      "earth-years-admin-2",
      "earth-years-admin-3",
      "earth-years-admin-4",
    ],
  },
  {
    label: "Double Coverage",
    metrics: [
      "double-covered-admin-1",
      "double-covered-admin-2",
      "double-covered-admin-3",
      "double-covered-admin-4",
    ],
  },
  {
    label: "Duplicates",
    metrics: ["dupes"],
  },
];

/**
 * Display labels for metrics in the diff-page dropdown.
 *
 * More descriptive than METRIC_DOCS labels for metrics whose METRIC_DOCS label
 * relies on chart-section context (e.g. "admin1" → "admin1 Earth Years").
 */
export const METRIC_LABELS = {
  "nonclosed-ring": "Non-closed Rings",
  "ring-self-intersect": "Ring Self-intersects",
  "self-intersect": "Self-intersects",
  "uncontained-inner-ring": "Uncontained inner",
  "nested-shells": "Nested Rings",
  "no-shapely": "Shapely Error",
  other: "Other",
  "invalid-way-reference": "Invalid Way Reference",
  "chronology-member-outside-range": "Member Outside Parent Range",
  "chronology-overlapping-members": "Overlapping Members",
  "chronology-undated-member": "Undated Members",
  "date-in-name": "Date Ranges in name",
  "date-invalid": "Invalid Dates",
  "date-end-no-start": "end_date w/o start_date",
  "date-far-future": "Far future",
  "date-start-after-end": "start_date > end_date",
  "date-edtf-invalid": "Invalid EDTF date",
  "date-edtf-mismatch": "Mismatched EDTF date",
  "earth-years-admin-1": "admin1 Earth Years",
  "earth-years-admin-2": "admin2 Earth Years",
  "earth-years-admin-3": "admin3 Earth Years",
  "earth-years-admin-4": "admin4 Earth Years",
  "double-covered-admin-1": "admin1 Double Coverage",
  "double-covered-admin-2": "admin2 Double Coverage",
  "double-covered-admin-3": "admin3 Double Coverage",
  "double-covered-admin-4": "admin4 Double Coverage",
  dupes: "Duplicate Relations",
};

/** Replace r/NNNNN, w/NNNNN, n/NNNNN with links to openhistoricalmap.org. */
export function formatExample(txt) {
  return txt
    .replaceAll(
      /\br\/(\d+)/g,
      '<a href="https://www.openhistoricalmap.org/relation/$1" target="_blank">r/$1</a>',
    )
    .replaceAll(
      /\bw\/(\d+)/g,
      '<a href="https://www.openhistoricalmap.org/way/$1" target="_blank">w/$1</a>',
    )
    .replaceAll(
      /\bn\/(\d+)/g,
      '<a href="https://www.openhistoricalmap.org/node/$1" target="_blank">n/$1</a>',
    );
}
