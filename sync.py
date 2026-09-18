#!/usr/bin/env python3
"""Stáhne iCal kalendáře (Booking.com, e-chalupy, Airbnb…), sloučí obsazené dny
a uloží je do docs/<web>.json a docs/<web>.ics. Konfigurace: feeds.json."""
import json, re, sys, urllib.request, datetime
from pathlib import Path

ROOT = Path(__file__).parent
UA = "Mozilla/5.0 (compatible; WebhunterKalendar/1.0)"

def stahni(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/calendar,*/*"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")

def datum(s: str):
    s = s.strip()
    m = re.match(r"^(\d{4})(\d{2})(\d{2})", s)
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

def udalosti(ics: str):
    ics = ics.replace("\r\n ", "").replace("\n ", "")   # rozbalit zalomené řádky
    ven = []
    for blok in ics.split("BEGIN:VEVENT")[1:]:
        blok = blok.split("END:VEVENT")[0]
        od = de = None
        souhrn = ""
        for r in blok.splitlines():
            if r.startswith("DTSTART"): od = datum(r.split(":", 1)[1])
            elif r.startswith("DTEND"): de = datum(r.split(":", 1)[1])
            elif r.startswith("SUMMARY"): souhrn = r.split(":", 1)[1].strip()
        if od and de and de > od:
            ven.append({"od": od.isoformat(), "do": de.isoformat(), "popis": souhrn[:60]})
    return ven

def main():
    konfig = json.loads((ROOT / "feeds.json").read_text())
    ROOT.joinpath("docs").mkdir(exist_ok=True)
    prehled = {}
    for web, data in konfig.items():
        vse, zdroje = [], []
        for z in data.get("feeds", []):
            try:
                ud = udalosti(stahni(z["url"]))
                vse += ud
                zdroje.append({"nazev": z.get("nazev", "kalendář"), "udalosti": len(ud), "stav": "ok"})
            except Exception as e:
                zdroje.append({"nazev": z.get("nazev", "kalendář"), "udalosti": 0, "stav": f"chyba: {str(e)[:80]}"})
        vse.sort(key=lambda u: u["od"])
        vystup = {"web": web, "aktualizovano": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                  "zdroje": zdroje, "obsazeno": vse}
        (ROOT / "docs" / f"{web}.json").write_text(json.dumps(vystup, ensure_ascii=False, indent=1))
        rad = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Webhunter//Kalendar//CS", "CALSCALE:GREGORIAN"]
        for i, u in enumerate(vse, 1):
            rad += ["BEGIN:VEVENT", f"UID:{web}-{i}@webhunter", f"DTSTART;VALUE=DATE:{u['od'].replace('-','')}",
                    f"DTEND;VALUE=DATE:{u['do'].replace('-','')}", "SUMMARY:Obsazeno", "END:VEVENT"]
        rad.append("END:VCALENDAR")
        (ROOT / "docs" / f"{web}.ics").write_text("\r\n".join(rad))
        prehled[web] = {"obsazenych_useku": len(vse), "zdroje": zdroje}
        print(web, "→", len(vse), "obsazených úseků", zdroje)
    (ROOT / "docs" / "index.json").write_text(json.dumps(prehled, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
