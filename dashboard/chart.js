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

  "earth-years-admin-1": { label: "admin1" },
  "earth-years-admin-2": { label: "admin2" },
  "earth-years-admin-3": { label: "admin3" },
  "earth-years-admin-4": { label: "admin4" },

  "num-nodes": { label: "Nodes" },
  "num-ways": { label: "Ways" },
  "num-relations": { label: "Relations" },
};

const response = await fetch("/dashboard/stats.csv");
const data = await response.text();
const [headerRow, ...rowStrs] = data.split("\r\n").slice(0, -1);
const header = headerRow.split(",");
const rows = rowStrs.map((rs) => rs.split(","));

function dataForSeries(...series) {
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
  idxs.sort((a, b) => lastRow[b] - lastRow[a]);
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
  const g = new Dygraph(chartEl, dataForSeries(...series), {
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
      const r = await fetch(`/daily/${date}/${metric}.examples.txt`);
      const text = await r.text();
      const examples = text.split("\n");
      const lis = examples.map((txt) => `<li>${formatExample(txt)}</li>`);
      examplesEl.innerHTML = `
        <div class="close-example">&times;</div>
        <div class="example-header">${label}: ${value} on ${date}</div>
        <div class="example-explanation">${help} (${metric})</div>
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
    dateWindow: [oneYearAgoMs, Date.now()]
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
  ["date-in-name",
  "date-invalid",
  "date-end-no-start"],
  {
    examples: true,
    axes: { y: { valueFormatter: x => String(x) } },
  }
);

makeChart(
  document.getElementById('earth-coverage'),
  ["earth-years-admin-1",
  "earth-years-admin-2",
  "earth-years-admin-3",
  "earth-years-admin-4"],
  {
    ylabel: 'Earth Years',
    examples: false,
    labelsKMB: false,
  }
);

makeChart(
  document.getElementById('raw-features'),
  [
    "num-nodes",
    "num-ways",
    "num-relations"
  ],
  {
    logscale: true,
    examples: false,
  }
);
