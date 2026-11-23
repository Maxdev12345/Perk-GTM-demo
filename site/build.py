"""Inject the latest pipeline run into the page template -> index.html."""
import json
import pathlib

here = pathlib.Path(__file__).resolve().parent
run = json.loads((here.parent / "prototype" / "out" / "run_output.json").read_text())
data = json.dumps(run, separators=(",", ":")).replace("</", "<\\/")
html = (here / "template.html").read_text().replace("/*__RUN_DATA__*/", data)
(here / "index.html").write_text(html)
print(f"index.html written ({len(html) // 1024} KB)")
