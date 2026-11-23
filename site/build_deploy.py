"""Standalone build for public hosting: full HTML document, slimmed run data."""
import json, pathlib, re
here = pathlib.Path(__file__).resolve().parent
run = json.loads((here.parent / "prototype" / "out" / "run_output.json").read_text())
keep_acc = ["id","domain","name","region","industry","is_customer","country","employees","countries","current_tool",
            "products","open_opportunity","last_contacted_days","finance_contact","enrichment"]
for d in run["decisions"]:
    d["account"] = {k: d["account"][k] for k in keep_acc if k in d["account"]}
    d["account"]["enrichment"].pop("sources", None)
    for k in ("routing_notes","play_meta","duplicate","crm_payload"): d.pop(k, None)
    for x in d["scores"]["active_signals"]: x.pop("source", None)
    d["brief"].pop("why_now", None)
for s in run["signals_catalog"].values(): pass
data = json.dumps(run, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
t = (here / "template.html").read_text().replace("/*__RUN_DATA__*/", data)
head, body = t.split('<header class="topbar">', 1)
head = re.sub(r"\n\s+", "\n", head)
reset = "<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>"
html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="GTM engineering proposal by Massimo Mauri for the Director of GTM Engineering role at Perk.">\n'
        '<meta name="robots" content="noindex">\n'
        + reset + "\n" + head + '</head>\n<body>\n<header class="topbar">' + body + "\n</body>\n</html>\n")
html = re.sub(r"\n[ \t]+", "\n", html)
html = re.sub(r"/\* -{3,}[^*]*-{3,} \*/", "", html)
out = here.parent / "deploy"; out.mkdir(exist_ok=True)
(out / "index.html").write_text(html)
print(len(html.encode()), "bytes")
