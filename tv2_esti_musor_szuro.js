import fs from "fs"
import { XMLParser } from "fast-xml-parser"

// EPG betöltése
const xml = fs.readFileSync("epg.xml", "utf8")

const parser = new XMLParser({ ignoreAttributes: false })
const adat = parser.parse(xml)

const musorok = adat.tv.programme || []

// mai dátum (YYYY-MM-DD)
const ma = new Date().toISOString().slice(0, 10)

// TV2 esti műsorok szűrése
const kimenet = musorok
  .filter(m =>
    (m["@_channel"] || "").toLowerCase().includes("tv2") &&
    (m["@_start"] || "").startsWith(ma) &&
    parseInt(m["@_start"].slice(8, 10)) >= 20
  )
  .map(m => ({
    kezdes: m["@_start"],
    vege: m["@_stop"],
    cim: typeof m.title === "string" ? m.title : m.title?.["#text"] || "",
    leiras: typeof m.desc === "string" ? m.desc : m.desc?.["#text"] || ""
  }))

fs.writeFileSync(
  "tv2_esti_musor.json",
  JSON.stringify(kimenet, null, 2)
)

console.log("OK: tv2_esti_musor.json elkészült")
