const response = await fetch("stats.csv");
const data = await response.text();
const [headerRow, ...rowStrs] = data.split("\r\n").slice(0, -1);
const header = headerRow.split(",");
const rows = rowStrs.map((rs) => rs.split(","));

function dataForSeries(...series) {
  const idxs = [0]; // always include date
  for (const s of series) {
    const idx = header.indexOf(s);
    if (idx === -1) {
      throw new Error(`Series "${s}" does not exist.`);
    }
    idxs.push(idx);
  }

  const sliceRows = [];
  for (const fullRow of [header].concat(rows)) {
    const row = idxs.map((idx) => fullRow[idx]);
    sliceRows.push(row);
  }
  const text = sliceRows.map((row) => row.join(",")).join("\n");
  console.log(text);
  return text;
}

const gGeom = new Dygraph(
  document.getElementById("geometry-errors"),
  dataForSeries(
    "nonclosed-ring",
    "ring-self-intersect",
    "self-intersect",
    "uncontained-inner-ring",
    "nested-shells",
    "no-shapely",
    "other",
  ),
  {},
);

const gChron = new Dygraph(
  document.getElementById("chronology-errors"),
  dataForSeries(
    "chronology-member-outside-range",
    "chronology-overlapping-members",
    "chronology-undated-member",
  ),
  {},
);

const gTags = new Dygraph(
  document.getElementById("tag-errors"),
  dataForSeries(
    "dates-in-names",
    "invalid-date"
  ),
  {},
);