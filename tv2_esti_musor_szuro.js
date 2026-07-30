import fs from "fs"
import { XMLParser } from "fast-xml-parser"
const MA = new Date().toISOString().slice(0, 10).replace(/-/g, "")
const DEL = "120000"
const NUMERIC_CHANNELS = {
  "139": "AMC",
  "42": "AXN"
}
const CSATORNAK = [
  "TV2",
  "SUPERTV2",
  "RTL",
  "RTL_HAROM",
  "AMC",
  "AXN",
  "VIASAT3",
  "VIASAT6",
  "FILM4",
  "FILMMANIA",
  "FILMCAFE",
  "FILMPLUSSZ",
  "VIASAT_FILM",
  "MOZIPLUSZ",
  "MOZIVERZUM",
  "OZONETV",
  "NICKELODEON"
];
function formatDatum(datum) {
  if (!datum || datum.length < 20) return datum;
  const alap = datum.slice(0, 14);
  const zona = datum.slice(14);
  const ev = alap.slice(0, 4);
  const honap = alap.slice(4, 6);
  const nap = alap.slice(6, 8);
  const ora = alap.slice(8, 10);
  const perc = alap.slice(10, 12);
  const mp = alap.slice(12, 14);
  return `${ev}.${honap}.${nap}  -  ${ora}:${perc}:${mp}${zona}`;
}
const xml = fs.readFileSync("epg.xml", "utf8")
const parser = new XMLParser({ ignoreAttributes: false })
const adat = parser.parse(xml)
const musorok = adat?.tv?.programme || []
const seen = new Set()
const kimenet = musorok
  .filter(m => {
    const ch = m["@_channel"] || "";
    const start = m["@_start"] || "";
    const title =
      typeof m.title === "string"
        ? m.title
        : m.title?.["#text"] || "";
    if (
      !(
        (CSATORNAK.includes(ch) || NUMERIC_CHANNELS[ch]) &&
        start.startsWith(MA) &&
        start.slice(8, 14) >= DEL
      )
    ) {
      return false;
    }
    const key = `${ch}|${start}|${title}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  })
  .map(m => ({
    csatorna: NUMERIC_CHANNELS[m["@_channel"]] || m["@_channel"],
    kezdes: formatDatum(m["@_start"]),
    vege: formatDatum(m["@_stop"]),
    cim:
      typeof m.title === "string"
        ? m.title
        : m.title?.["#text"] || ""
  }));
fs.writeFileSync(
  "tv2_esti_musor.json",
  JSON.stringify(kimenet, null, 2)
)
console.log("Mai műsorok déltől:", kimenet.length)
