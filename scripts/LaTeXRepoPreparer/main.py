import subprocess
import json
import os

def get_file_edit_info(file_path):
    p = subprocess.Popen(["git", "log", "-1", "--format=%h %ct", "--", file_path],
        cwd="/app/workspace/repo",
        stdout=subprocess.PIPE)
    p.wait()
    
    assert p.returncode == 0
    
    output_str = p.stdout.read().decode("UTF-8")
    
    if len(output_str.strip()) == 0:
        return None

    commit_hash = output_str.split(" ")[0]
    unix_timestamp = int(output_str.split(" ")[1])
    
    return {
        "hash": commit_hash,
        "timestamp": unix_timestamp
    }
    
def walk_file(git_file_path):
    infos = {}
    
    info = get_file_edit_info(git_file_path)
    if not info:
        return {}
    infos[git_file_path] = info
    
    file_path = os.path.join("/app/workspace/repo", git_file_path)
    if not os.path.isdir(file_path):
        return infos

    for name in os.listdir(file_path):
        sub_path = os.path.join(git_file_path, name)
        infos.update(walk_file(sub_path))

    return infos

with open("/app/vars.json") as f:
    data = json.load(f)
repo_url = data["repo_url"]
p = subprocess.Popen(["git", "clone", repo_url, "repo"],
        cwd="/app/workspace")
p.wait()
assert p.returncode == 0

edit_infos = walk_file(".")
with open("/app/output/run/git_file_edit_infos.json", "w") as f:
    json.dump(edit_infos, f)

with open("/app/output/output.json", "w") as f:
    json.dump({
        "new_tasks": [
            {
                "script": "LaTeXCombiner",
                "data": {
                    "input_files": [
                        {
                            "server": {
                                "folder": "global",
                                "path": "LaTeX/last_build_times.json"
                            },
                            "client": "last_build_times.json"
                        },
                        {
                            "server": {
                                "folder": "run",
                                "run_id": "parent",
                                "path": "git_file_edit_infos.json"
                            },
                            "client": "git_file_edit_infos.json"
                        },
                        {
                            "server": {
                                "folder": "run",
                                "run_id": "parent",
                                "path": "repo"
                            },
                            "client": "repo"
                        },
                    ],
                }
            }
        ]
    }, f)