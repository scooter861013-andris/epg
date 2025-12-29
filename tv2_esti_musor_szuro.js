import fs from "fs"
import { XMLParser } from "fast-xml-parser"

const xml = fs.readFileSync("epg.xml", "utf8")

const parser = new XMLParser({ ignoreAttributes: false })
const adat = parser.parse(xml)

const musorok = adat.tv.programme || []

const kimenet = musorok
  .filter(m => {
    const csatorna = m["@_channel"]
    const start = m["@_start"] || ""
    const ora = parseInt(start.slice(8, 10))

    // category lehet string vagy objektum
    const kategoriak = Array.isArray(m.category)
      ? m.category
      : [m.category]

    const film = kategoriak?.some(k =>
      (typeof k === "string" && k === "film") ||
      (k?.["#text"] === "film")
    )

    return (
      csatorna === "TV2.hu@SD" &&
      film &&
      ora >= 20
    )
  })
  .map(m => ({
    kezdes: m["@_start"],
    vege: m["@_stop"],
    cim: typeof m.title === "string" ? m.title : m.title?.["#text"] || "",
    leiras: typeof m.desc === "string" ? m.desc : m.desc?.["#text"] || ""
  }))

fs.writeFileSync("tv2_esti_musor.json", JSON.stringify(kimenet, null, 2))
console.log("TV2 esti filmek:", kimenet.length)
