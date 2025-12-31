import fs from "fs"
import { XMLParser } from "fast-xml-parser"

const MA = new Date().toISOString().slice(0, 10).replace(/-/g, "")
const DEL = "120000" // 12:00-tól

const NUMERIC_CHANNELS = {
  "139": "AMC",
  "42": "AXN"
}

const CSATORNAK = [
  "TV2",
  "SUPERTV2",
  "RTL",
  "RTL_KETTO",
  "RTL_HAROM",
  "AMC",
  "AXN",
  "VIASAT3",
  "VIASAT6",
  "FILMMANIA",
  "FILMCAFE",
  "FILMPLUSSZ",
  "VIASAT_FILM",
  "MOZIPLUSZ",
  "PARAMOUNT_NETWORK",
  "OZONETV",
  "NICKELODEON"
];


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

    // --- alap szűrés (mint eddig) ---
    if (
      !(
        (CSATORNAK.includes(ch) || NUMERIC_CHANNELS[ch]) &&
        start.startsWith(MA) &&
        start.slice(8, 14) >= DEL
      )
    ) {
      return false;
    }

    // --- DUPLIKÁLÁS VÉDELEM ---
    const key = `${ch}|${start}|${title}`;
    if (seen.has(key)) return false;
    seen.add(key);

    return true;
  })
  .map(m => ({
    csatorna: NUMERIC_CHANNELS[m["@_channel"]] || m["@_channel"],
    kezdes: m["@_start"],
    vege: m["@_stop"],
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
