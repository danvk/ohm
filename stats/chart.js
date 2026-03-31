const response = await fetch("stats.csv");
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
  const lastRow = [''].concat(rows.at(-1).slice(1).map(v => Number(v)));
  idxs.sort((a, b) => lastRow[b] - lastRow[a]);
  const allIdxs = [0].concat(idxs);  // always include the date

  const sliceRows = [];
  for (const fullRow of [header].concat(rows)) {
    const row = allIdxs.map((idx) => fullRow[idx]);
    sliceRows.push(row);
  }
  const text = sliceRows.map((row) => row.join(",")).join("\n");
  return text;
}

function makeChart(container, ...series) {
  const chartEl = container.querySelector('.chart');
  const labelsEl = container.querySelector('.chart-labels');
  const g = new Dygraph(
    chartEl,
    dataForSeries(
      ...series
    ),
    {
      labelsDiv: labelsEl,
      labelsSeparateLines: true,
      legend: 'always',
      xRangePad: 5,
      labelsKMB: true,
      hideOverlayOnMouseOut: false,
    },
  );
  g.setSelection(rows.length - 1);
}

makeChart(document.getElementById('geometry-errors'),
 "nonclosed-ring",
 "ring-self-intersect",
 "self-intersect",
 "uncontained-inner-ring",
 "nested-shells",
 "no-shapely",
 "other");

makeChart(
  document.getElementById("chronology-errors"),
  "chronology-member-outside-range",
  "chronology-overlapping-members",
  "chronology-undated-member",
);

makeChart(
  document.getElementById("tag-errors"),
  "dates-in-names",
  "invalid-date"
);
