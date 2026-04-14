const DFEAULT_COLOR = "#6080C0";  // — blue
const PALETTE = [
  DFEAULT_COLOR,
  "#E15759",  // — red
  "#4E9F3D",  // — green
  "#F28E2B",  // — orange
  "#B07AA1",  // — purple
  "#76B7B2",  // — teal
  "#EDC948",  // — yellow
  "#9C755F",  // — brown
  '#FF9DA7',  // - pink
];

const METRIC_DOCS = {
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
    help: "Either start_date or end_date is after 2050. This is often a typo or placeholder, but omitting end_date is preferable."
  },

  "earth-years-admin-1": { label: "admin1", help: 'See above for an explanation of this metric.' },
  "earth-years-admin-2": { label: "admin2", help: 'See above for an explanation of this metric.' },
  "earth-years-admin-3": { label: "admin3", help: 'See above for an explanation of this metric.' },
  "earth-years-admin-4": { label: "admin4", help: 'See above for an explanation of this metric.' },

  'double-covered-admin-1': { label: "admin1", help: '' },
  'double-covered-admin-2': { label: "admin2", help: '' },
  'double-covered-admin-3': { label: "admin3", help: '' },
  'double-covered-admin-4': { label: "admin4", help: '' },

  "num-nodes": { label: "Nodes" },
  "num-ways": { label: "Ways" },
  "num-relations": { label: "Relations" },
  "dupes": {
    label: "Duplicate Relations",
    help: "Number of relations that have a likely duplicate. " +
    "Each set of likely duplicates counts once."
  }
};

const response = await fetch("/dashboard/stats.csv");
const data = await response.text();
const [headerRow, ...rowStrs] = data.split("\r\n").slice(0, -1);
const header = headerRow.split(",");
const rows = rowStrs.map((rs) => rs.split(","));

function dataForSeries(series, opts) {
  const idxs = [];
  for (const s of series) {
    const idx = header.indexOf(s);
    if (idx === -1) {
      throw new Error(`Series "${s}" does not exist.`);
    }
    idxs.push(idx);
  }
  const lastRow = [""].concat(
    rows
      .at(-1)
      .slice(1)
      .map((v) => Number(v)),
  );
  if (!opts?.doNotSort) {
    idxs.sort((a, b) => lastRow[b] - lastRow[a]);
  }
  const allIdxs = [0].concat(idxs); // always include the date

  const sliceRows = [];
  for (const fullRow of [header].concat(rows)) {
    const row = allIdxs.map((idx) => fullRow[idx]);
    sliceRows.push(row);
  }
  const text = sliceRows.map((row) => row.join(",")).join("\n");
  return text;
}

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

function makeChart(container, series, options) {
  const chartEl = container.querySelector(".chart");
  const labelsEl = container.querySelector(".chart-labels");
  const data = Array.isArray(series) ? dataForSeries(series) : series;
  const g = new Dygraph(chartEl, data, {
    labelsDiv: labelsEl,
    labelsSeparateLines: true,
    legend: "always",
    xRangePad: 5,
    labelsKMB: true,
    hideOverlayOnMouseOut: false,
    colors: PALETTE,
    legendFormatter: (data) => {
      if (data.x == null) {
        // This should only be a temporary state, until the setSelection() kicks in.
        return "";
      }

      var html = data.xHTML;
      const rawDate = rows[data.i][0];
      data.series.forEach(function (series) {
        if (!series.isVisible) return;
        const { label, help } = METRIC_DOCS[series.label];
        let nameOrLink = `${series.yHTML}`;
        if (options.examples) {
          nameOrLink = `<a data-date="${rawDate}" data-series="${series.label}" class="count" href="#">${nameOrLink}</a>`;
        }
        const labelHtml = `<span class="series-name" style="color: ${series.color}" title="${help}">${label}</span>: ${nameOrLink}`;
        html += `<br>${series.dashHTML} ${labelHtml}`;
      });
      return html;
    },
    ...options,
  });
  g.setSelection(rows.length - 1);

  if (options.examples) {
    const examplesEl = container.querySelector(".examples");
    labelsEl.addEventListener("click", async (e) => {
      const a = e.target;
      const date = a.getAttribute("data-date");
      const metric = a.getAttribute("data-series");
      if (!date || !metric) return;
      e.preventDefault();
      e.stopPropagation();
      const value = a.textContent;
      const { label, help } = METRIC_DOCS[metric];
      const examplesUrl = `/daily/${date}/${metric}.examples.txt`;
      const r = await fetch(examplesUrl);
      const text = await r.text();
      const examples = text.split("\n");
      const lis = examples.map((txt) => `<li>${formatExample(txt)}</li>`);
      examplesEl.innerHTML = `
        <div class="close-example">&times;</div>
        <div class="example-header">${label}: ${value} on ${date}</div>
        <div class="example-explanation">
          ${help} (${metric}) <a href="${examplesUrl}" target="_blank">raw</a>
        </div>
        <ul>
          ${lis.join("")}
        </ul>
      `;
      examplesEl.querySelector(".close-example").addEventListener("click", () => {
        examplesEl.textContent = "";
      });
    });
  }
}

const oneYearAgoMs = new Date(new Date().setFullYear(new Date().getFullYear() - 1)).getTime();

makeChart(
  document.getElementById("geometry-errors"),
  [
  "nonclosed-ring",
  "ring-self-intersect",
  "self-intersect",
  "uncontained-inner-ring",
  "nested-shells",
  "no-shapely",
  "other"],
  {
    examples: true,
    axes: { y: { valueFormatter: x => String(x) } },
    dateWindow: [Date.parse('2026-01-01'), Date.now()]
  }
);

makeChart(
  document.getElementById("chronology-errors"),
  ["chronology-member-outside-range",
  "chronology-overlapping-members",
  "chronology-undated-member"],
  {
    examples: true,
    axes: { y: { valueFormatter: x => String(x) } },
  }
);

makeChart(
  document.getElementById("tag-errors"),
  [
    "date-in-name",
    "date-invalid",
    "date-end-no-start",
    "date-far-future",
    "date-start-after-end"
  ],
  {
    examples: true,
    connectSeparatedPoints: true,
    axes: { y: { valueFormatter: x => String(x) } },
    dateWindow: [Date.parse('2026-01-01'), Date.now()]
  }
);

makeChart(
  document.getElementById('earth-coverage'),
  [
    "earth-years-admin-1",
    "earth-years-admin-2",
    "earth-years-admin-3",
    "earth-years-admin-4"
  ],
  {
    ylabel: 'Earth Years',
    examples: true,
    labelsKMB: false,
  }
);

makeChart(
  document.getElementById('overlap'),
  [
    "double-covered-admin-1",
    "double-covered-admin-2",
    "double-covered-admin-3",
    "double-covered-admin-4"
  ],
  {
    ylabel: 'Earth Years',
    examples: true,
    labelsKMB: false,
    connectSeparatedPoints: true,
    dateWindow: [Date.parse('2026-01-01'), Date.now()]
  }
);

makeChart(
  document.getElementById('dupes'),
  [
    'dupes'
  ],
  {
    examples: true,
    dateWindow: [Date.parse('2026-03-31'), Date.now()]
  }
);

{
  const rawCounts = dataForSeries(['num-relations', 'num-ways', 'num-nodes'], {doNotSort: true});
  const [header, ...rows] = rawCounts.split('\n').map(row => row.split(','));
  const initVals = rows[0].map((v, i) => i > 0 ? Number(v) : 0);
  const vals = rows.map(row => row.map((v, i) => i === 0 ? v : Number(v) / initVals[i]));
  const text = [header, ...vals].map(row => row.map(String).join(',')).join('\n');

  makeChart(document.getElementById('raw-features'), text, {
    examples: false,
    axes: { y: { valueFormatter: (scaled, _a, _b, _c, row, col) => {
      const rawVal = Number(rows[row][col]);
      const rawStr = rawVal.toLocaleString();
      const scaleStr = scaled.toLocaleString({numeric: {maximumSignificantDigits: 2}});
      return `${rawStr} (${scaleStr}x)`;
    }}}
  })
}
