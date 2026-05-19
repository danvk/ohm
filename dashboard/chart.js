import { SERVER, METRIC_DOCS, formatExample } from "./metrics.js";

const DEFAULT_COLOR = "#6080C0";  // — blue
const PALETTE = [
  DEFAULT_COLOR,
  "#E15759",  // — red
  "#4E9F3D",  // — green
  "#F28E2B",  // — orange
  "#B07AA1",  // — purple
  "#76B7B2",  // — teal
  "#EDC948",  // — yellow
  "#9C755F",  // — brown
  '#FF9DA7',  // - pink
];

const response = await fetch(`${SERVER}/dashboard/stats.csv`);
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
      const examplesUrl = `${SERVER}/daily/${date}/${metric}.examples.txt`;
      const r = await fetch(examplesUrl);
      const text = await r.text();
      const examples = text.split("\n");
      const lis = examples.map((txt) => `<li>${formatExample(txt)}</li>`);
      const dateIdx = rows.findIndex((row) => row[0] === date);
      const prevDate = dateIdx > 0 ? rows[dateIdx - 1][0] : null;
      const diffLink = prevDate
        ? ` <a href="/dashboard/diff/?metric=${metric}&day1=${prevDate}&day2=${date}" target="_blank">diff</a>`
        : "";
      examplesEl.innerHTML = `
        <div class="close-example">&times;</div>
        <div class="example-header">${label}: ${value} on ${date}</div>
        <div class="example-explanation">
          ${help} (${metric}) <a href="${examplesUrl}" target="_blank">raw</a>${diffLink}
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
    "date-start-after-end",
    "date-edtf-invalid",
    "date-edtf-mismatch",
  ],
  {
    examples: true,
    // connectSeparatedPoints: true,
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
