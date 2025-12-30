import fs from "fs"
import { XMLParser } from "fast-xml-parser"

const MA = new Date().toISOString().slice(0, 10).replace(/-/g, "") // ← EZ AZ 1.

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

const xml = fs.readFileSync("epg.xml", "utf8")
const parser = new XMLParser({ ignoreAttributes: false })
const adat = parser.parse(xml)

const musorok = adat?.tv?.programme || []

const kimenet = musorok
  .filter(m =>
    CSATORNAK.includes(m["@_channel"]) &&
    (m["@_start"] || "").startsWith(MA)   // ← EZ A 2.
  )
  .map(m => ({
    csatorna: m["@_channel"],
    kezdes: m["@_start"],
    vege: m["@_stop"],
    cim: typeof m.title === "string" ? m.title : m.title?.["#text"] || "",
    leiras: typeof m.desc === "string" ? m.desc : m.desc?.["#text"] || ""
  }))

fs.writeFileSync(
  "tv2_esti_musor.json",
  JSON.stringify(kimenet, null, 2)
)

console.log("Mai műsorok száma:", kimenet.length)
