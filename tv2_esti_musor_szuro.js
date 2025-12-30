import fs from "fs"
import { XMLParser } from "fast-xml-parser"

// --------- MAI NAP (UTC, YYYYMMDD) ----------
const ma = new Date().toISOString().slice(0, 10).replace(/-/g, "")

// --------- CSATORNALISTA ----------
const CSATORNAK = [
  "RTL.hu@SD",
  "TV2.hu@SD",
  "Viasat3.hu@SD",
  "SuperTV2.hu@SD",
  "FilmCafe.hu@Hungary",
  "FilmPlus.hu@SD",
  "FilmMania.hu@SD",
  "MoziPlus.hu@SD",
  "RTLHarom.hu@SD",
  "ParamountNetwork.hu@SD"
]

// --------- XML BEOLVASÁS ----------
const xml = fs.readFileSync("epg.xml", "utf8")

const parser = new XMLParser({ ignoreAttributes: false })
const adat = parser.parse(xml)

const musorok = adat?.tv?.programme || []

// --------- SZŰRÉS ----------
const kimenet = musorok
  .filter(m => {
    const csatorna = m["@_channel"]
    const start = m["@_start"] || ""

    if (!CSATORNAK.includes(csatorna)) return false
    if (!start.startsWith(ma)) return false   // 🔴 CSAK MA

    const kategoriak = Array.isArray(m.category)
      ? m.category
      : [m.category]

    const film = kategoriak?.some(k =>
      (typeof k === "string" && k === "film") ||
      (k?.["#text"] === "film")
    )

    return film
  })
  .map(m => ({
    csatorna: m["@_channel"],
    kezdes: m["@_start"],
    vege: m["@_stop"],
    cim: typeof m.title === "string" ? m.title : m.title?.["#text"] || "",
    leiras: typeof m.desc === "string" ? m.desc : m.desc?.["#text"] || ""
  }))

// --------- JSON KIÍRÁS ----------
fs.writeFileSync(
  "tv_musor_ma.json",
  JSON.stringify(kimenet, null, 2)
)

console.log("Mai filmek száma:", kimenet.length)
