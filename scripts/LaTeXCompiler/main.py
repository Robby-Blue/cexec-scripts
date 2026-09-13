import subprocess
import shutil
import sys
import os
import json

import pymupdf

def docs_equal(last_doc, doc):
    if last_doc is None:
        return False, 0
    if last_doc.page_count != doc.page_count:
        return False, 0
    
    for i, (last_doc_page, doc_page) in enumerate(zip(last_doc, doc)):
        if last_doc_page.get_text("words") != doc_page.get_text("words"):
            return False, i
    return True, 0

def compile():
    p = subprocess.Popen(["lualatex", "--shell-escape",
        "-interaction=nonstopmode", "-halt-on-error", 
        "-output-directory=/app/workspace",
        "/app/workspace/main.tex"],
        cwd="/app/workspace")
    
    p.wait()

    doc = pymupdf.open("/app/workspace/main.pdf")
    return doc

def is_top_level_doc():
    if not os.path.exists("/app/vars.json"):
        return False, None
    with open("/app/vars.json", "r") as f:
        data = json.load(f)
        return data.get("is_top_level_doc", False), data.get("name", None)

sub_best_recompile_count = 0
best_page = 0

compile_count = 0
last_doc = None
while True:
    compile_count += 1
    doc = compile()

    docs_are_equal, page = docs_equal(last_doc, doc)
    
    print(f"{docs_are_equal=}, {page=}")
    
    if docs_are_equal:
        break
    else:
        if page > best_page:
            best_page = page
            sub_best_recompile_count = 0
        else:
            sub_best_recompile_count += 1
            print(f"{sub_best_recompile_count=}")
            if sub_best_recompile_count >= 10:
                print("recompiled too often. quitting")
                sys.exit(1)
    
    last_doc = doc

shutil.copy("/app/workspace/main.pdf", "/app/output/run")
shutil.copy("/app/workspace/anki.txt", "/app/output/run")

should_send, name = is_top_level_doc()
if should_send:
    with open("/app/output/output.json", "w") as f:
        json.dump({
            "webhook": {
                "title": f"Compiled {name}",
                "embeds": [
                    {
                        "fields": [
                            {
                                "name": "Stats",
                                "value": f"Pages: {last_doc.page_count}\nCompilation Count: {compile_count}",
                                "inline": False
                            },
                        ],
                    }
                ],
                "include_file": {
                    "name": f"{name}.pdf",
                    "path": "run/main.pdf"
                }
            },
            "new_tasks": [
                {
                    "script": "AnkiDeckGenerator",
                    "data": {
                        "input_files": [{
                            "server": {
                                "folder": "run",
                                "run_id": "parent",
                                "path": "anki.txt"
                            },
                            "client": "anki.txt"
                        }],
                    }
                }
            ]
        }, f)