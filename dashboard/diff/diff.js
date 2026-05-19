const SERVER = 'http://localhost:8081';

// Metric labels and groupings, mirroring the categories in chart.js
const METRIC_GROUPS = [
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

const METRIC_LABELS = {
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

// Build a flat set of all metrics that appear in METRIC_GROUPS
const ALL_GROUPED_METRICS = new Set(METRIC_GROUPS.flatMap((g) => g.metrics));

/** Parse stats.csv to get available dates and the full set of metric column names. */
async function loadStats() {
  const response = await fetch(`${SERVER}/dashboard/stats.csv`);
  const text = await response.text();
  const [headerRow, ...dataRows] = text.split("\r\n").filter((r) => r.length > 0);
  const allColumns = headerRow.split(",");
  const dates = dataRows.map((row) => row.split(",")[0]).filter(Boolean);
  // Metrics are all non-date columns that have example files (appear in our groups,
  // or are present in stats.csv but not in our groups — shown ungrouped).
  const statsMetrics = new Set(allColumns.filter((c) => c !== "date"));
  return { dates, statsMetrics };
}

/** Replace r/NNNNN, w/NNNNN, n/NNNNN with OHM links. */
function formatExample(txt) {
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

/** Extract the OSM-style ID prefix (r/123, w/456, n/789) from an example line. */
function parseLineId(line) {
  const match = line.match(/^([rnw]\/\d+)/i);
  return match ? match[1].toLowerCase() : null;
}

/**
 * Compute a diff between two arrays of example lines.
 *
 * Returns rows tagged as 'removed', 'added', or 'changed', plus summary counts.
 */
function computeDiff(lines1, lines2) {
  const map1 = new Map(); // id -> original line
  const map2 = new Map();
  const order1 = []; // ordered list of unique ids seen in day1
  const order2 = [];

  for (const line of lines1) {
    if (!line.trim()) continue;
    const id = parseLineId(line) ?? line;
    if (!map1.has(id)) order1.push(id);
    map1.set(id, line);
  }
  for (const line of lines2) {
    if (!line.trim()) continue;
    const id = parseLineId(line) ?? line;
    if (!map2.has(id)) order2.push(id);
    map2.set(id, line);
  }

  const seen = new Set();
  const rows = [];

  // Walk day1 items: emit removed or changed rows
  for (const id of order1) {
    if (seen.has(id)) continue;
    seen.add(id);
    const d1 = map1.get(id);
    const d2 = map2.get(id);
    if (d2 === undefined) {
      rows.push({ type: "removed", left: d1, right: null });
    } else if (d1 !== d2) {
      rows.push({ type: "changed", left: d1, right: d2 });
    }
    // Unchanged items are not shown in the diff
  }

  // Walk day2 items: emit added rows for items not in day1
  for (const id of order2) {
    if (seen.has(id)) continue;
    seen.add(id);
    rows.push({ type: "added", left: null, right: map2.get(id) });
  }

  const removedCount = rows.filter((r) => r.type === "removed").length;
  const addedCount = rows.filter((r) => r.type === "added").length;
  const changedCount = rows.filter((r) => r.type === "changed").length;
  const unchangedCount = map1.size - removedCount - changedCount;

  return {
    rows,
    removedCount,
    addedCount,
    changedCount,
    unchangedCount,
    total1: map1.size,
    total2: map2.size,
  };
}

/** Render a computed diff into the output container. */
function renderDiff(outputEl, diff, day1, day2) {
  const { rows, removedCount, addedCount, changedCount, unchangedCount, total1, total2 } = diff;

  const parts = [];
  if (removedCount > 0) parts.push(`${removedCount} removed`);
  if (addedCount > 0) parts.push(`${addedCount} added`);
  if (changedCount > 0) parts.push(`${changedCount} changed`);
  parts.push(`${unchangedCount} unchanged`);

  const summaryHtml = `
    <p class="diff-summary">
      <strong>Day 1</strong> (${day1}): ${total1} items &nbsp;&mdash;&nbsp;
      <strong>Day 2</strong> (${day2}): ${total2} items<br>
      ${parts.join(", ")}
    </p>`;

  if (rows.length === 0) {
    outputEl.innerHTML = summaryHtml + '<p class="diff-no-changes">No changes between these two days.</p>';
    return;
  }

  const tableRows = rows
    .map((row) => {
      const leftHtml = row.left ? formatExample(row.left) : "";
      const rightHtml = row.right ? formatExample(row.right) : "";
      let leftClass = "";
      let rightClass = "";
      if (row.type === "removed") {
        leftClass = "diff-removed";
      } else if (row.type === "added") {
        rightClass = "diff-added";
      } else if (row.type === "changed") {
        leftClass = "diff-changed-left";
        rightClass = "diff-changed-right";
      }
      return `<tr>
        <td class="${leftClass}">${leftHtml}</td>
        <td class="${rightClass}">${rightHtml}</td>
      </tr>`;
    })
    .join("");

  outputEl.innerHTML =
    summaryHtml +
    `<table class="diff-table">
      <thead>
        <tr>
          <th>Day 1: ${day1}</th>
          <th>Day 2: ${day2}</th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>`;
}

/** Fetch an examples file; returns lines array, or null if not found. */
async function fetchExamples(date, metric) {
  const url = `${SERVER}/daily/${date}/${metric}.examples.txt`;
  const response = await fetch(url);
  if (!response.ok) return null;
  const text = await response.text();
  return text.split("\n").filter((l) => l.trim());
}

/** Populate a <select> element with <option> elements. */
function populateSelect(selectEl, options, selectedValue) {
  selectEl.innerHTML = "";
  for (const { value, label, group } of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    if (value === selectedValue) option.selected = true;
    selectEl.appendChild(option);
  }
}

/** Populate the metric <select> with optgroups from METRIC_GROUPS, plus ungrouped extras. */
function populateMetricSelect(selectEl, statsMetrics, selectedMetric) {
  selectEl.innerHTML = "";
  const covered = new Set();

  for (const group of METRIC_GROUPS) {
    const inStats = group.metrics.filter((m) => statsMetrics.has(m));
    if (inStats.length === 0) continue;
    const optgroup = document.createElement("optgroup");
    optgroup.label = group.label;
    for (const metric of inStats) {
      covered.add(metric);
      const option = document.createElement("option");
      option.value = metric;
      option.textContent = METRIC_LABELS[metric] ?? metric;
      if (metric === selectedMetric) option.selected = true;
      optgroup.appendChild(option);
    }
    selectEl.appendChild(optgroup);
  }

  // Add any stats.csv metrics not covered by the hardcoded groups
  const extras = [...statsMetrics].filter(
    (m) => !covered.has(m) && ALL_GROUPED_METRICS.has(m) === false,
  );
  if (extras.length > 0) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = "Other";
    for (const metric of extras.sort()) {
      const option = document.createElement("option");
      option.value = metric;
      option.textContent = METRIC_LABELS[metric] ?? metric;
      if (metric === selectedMetric) option.selected = true;
      optgroup.appendChild(option);
    }
    selectEl.appendChild(optgroup);
  }

  // If selectedMetric not found in any group, select the first available
  if (selectedMetric && !selectEl.querySelector(`option[value="${selectedMetric}"]`)) {
    if (selectEl.options.length > 0) selectEl.options[0].selected = true;
  }
}

/** Populate a date <select> with dates in reverse chronological order. */
function populateDateSelect(selectEl, dates, selectedDate) {
  selectEl.innerHTML = "";
  const reversed = [...dates].reverse();
  for (const date of reversed) {
    const option = document.createElement("option");
    option.value = date;
    option.textContent = date;
    if (date === selectedDate) option.selected = true;
    selectEl.appendChild(option);
  }
}

/** Read URL params, fetch data, and render the diff. */
async function run() {
  const params = new URLSearchParams(window.location.search);
  const statusEl = document.getElementById("diff-status");
  const outputEl = document.getElementById("diff-output");
  const metricSelect = document.getElementById("metric-select");
  const day1Select = document.getElementById("day1-select");
  const day2Select = document.getElementById("day2-select");

  statusEl.textContent = "Loading stats…";

  const { dates, statsMetrics } = await loadStats();

  // Filter metrics to those known to have example files
  const metricsWithExamples = new Set(
    [...statsMetrics].filter((m) => ALL_GROUPED_METRICS.has(m)),
  );

  // Determine initial selections from URL params, or sensible defaults
  const defaultMetric =
    params.get("metric") ||
    METRIC_GROUPS.flatMap((g) => g.metrics).find((m) => metricsWithExamples.has(m)) ||
    "";
  const defaultDay2 = params.get("day2") || dates.at(-1) || "";
  const defaultDay1 = params.get("day1") || dates.at(-2) || "";

  populateMetricSelect(metricSelect, metricsWithExamples, defaultMetric);
  populateDateSelect(day1Select, dates, defaultDay1);
  populateDateSelect(day2Select, dates, defaultDay2);

  async function refresh() {
    const metric = metricSelect.value;
    const day1 = day1Select.value;
    const day2 = day2Select.value;

    // Update URL without adding to browser history
    const newParams = new URLSearchParams({ metric, day1, day2 });
    history.replaceState(null, "", "?" + newParams.toString());

    outputEl.innerHTML = "";
    statusEl.textContent = `Loading examples for ${metric} on ${day1} and ${day2}…`;

    const [lines1, lines2] = await Promise.all([
      fetchExamples(day1, metric),
      fetchExamples(day2, metric),
    ]);

    if (!lines1 && !lines2) {
      statusEl.textContent = "";
      outputEl.innerHTML = `<p>No examples file found for <strong>${metric}</strong> on either ${day1} or ${day2}.</p>`;
      return;
    }
    if (!lines1) {
      statusEl.textContent = "";
      outputEl.innerHTML = `<p>No examples file found for <strong>${metric}</strong> on ${day1}.</p>`;
      return;
    }
    if (!lines2) {
      statusEl.textContent = "";
      outputEl.innerHTML = `<p>No examples file found for <strong>${metric}</strong> on ${day2}.</p>`;
      return;
    }

    statusEl.textContent = "";
    const diff = computeDiff(lines1, lines2);
    renderDiff(outputEl, diff, day1, day2);
  }

  metricSelect.addEventListener("change", refresh);
  day1Select.addEventListener("change", refresh);
  day2Select.addEventListener("change", refresh);

  await refresh();
}

run();
