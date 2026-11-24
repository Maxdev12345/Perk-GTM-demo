"""Build the SDR RevOps page: site/sdr.html (artifact) and docs/index.html (public, standalone)."""
import json, pathlib, re
here = pathlib.Path(__file__).resolve().parent
run = json.loads((here.parent / "prototype" / "out" / "run_output.json").read_text())
keep = ["id", "name", "region", "industry", "is_customer", "employees", "countries", "current_tool",
        "open_opportunity", "last_contacted_days", "finance_contact"]
slim = {"config_version": run["config_version"], "metrics": run["metrics"],
        "signals_catalog": {k: {"label": v["label"]} for k, v in run["signals_catalog"].items()},
        "decisions": []}
for d in run["decisions"]:
    if d["account"].get("is_customer"):
        continue
    s = d["scores"]
    slim["decisions"].append({
        "account": {k: d["account"][k] for k in keep if k in d["account"]},
        "pod": d["pod"], "play": d["play"],
        "scores": {"fit": s["fit"], "timing": s["timing"],
                   "active_signals": [{k: x[k] for k in ("type", "label", "days_ago", "evidence", "weight", "strength")} for x in s["active_signals"]],
                   "suppressed_signals": [{"type": x["type"]} for x in s["suppressed_signals"]]},
        "brief": {k: d["brief"][k] for k in ("opener", "confidence", "needs_review")},
    })
data = json.dumps(slim, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
page = (here / "template_sdr.html").read_text().replace("/*__RUN_DATA__*/", data)
(here / "sdr.html").write_text(page)
head, body = page.split('<header class="signbar">', 1)
doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       '<meta name="description" content="SDR and BDR operations proposal by Massimo Mauri for the Revenue Operations Manager role at Perk.">\n'
       '<meta name="robots" content="noindex">\n<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
       + head + '</head>\n<body>\n<header class="signbar">' + body + "\n</body>\n</html>\n")
doc = re.sub(r"\n[ \t]+", "\n", doc)
out = here.parent / "docs"; out.mkdir(exist_ok=True)
(out / "index.html").write_text(doc)
print("sdr.html", len(page) // 1024, "KB · docs/index.html", len(doc) // 1024, "KB")
