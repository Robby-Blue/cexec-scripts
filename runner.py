import docker
import json
import sys
import os

docker_client = docker.from_env()

def run_script(name):    
    scripts_path = os.path.abspath("scripts")
    script_path = os.path.join(scripts_path, name)
    config_path = os.path.join(script_path, "config.json")
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    image = config["image"]
    
    workspace_path = os.path.abspath("workspace")
    output_path = os.path.join(workspace_path, "output")
    output_global_path = os.path.join(output_path, "global")
    output_run_path = os.path.join(output_path, "run")
    input_path = os.path.join(workspace_path, "input")
    
    os.makedirs(workspace_path, exist_ok=True)
    
    del_dir(output_path)
    
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(output_global_path, exist_ok=True)
    os.makedirs(output_run_path, exist_ok=True)
    
    os.makedirs(input_path, exist_ok=True)
    
    workspace_mount = docker.types.Mount(target="/app/workspace", source=None, type="tmpfs")
    script_mount = docker.types.Mount(target="/app/script", source=script_path, type="bind", read_only=True)
    output_mount = docker.types.Mount(target="/app/output", source=output_path, type="bind")
    input_mount = docker.types.Mount(target="/app/input", source=input_path, type="bind", read_only=True)
    
    container = docker_client.containers.run(image,
        detach=True, tty=True,
        mounts=[workspace_mount, script_mount, output_mount, input_mount]
    )
    
    res = container.exec_run(["sh", "/app/script/entrypoint.sh"],
        workdir="/app/workspace")
    
    print(f"exit code: {res.exit_code}")
    print(5*"=" + " output " +30*"=")
    print(res.output.decode())
    print(5*"=" + " files " +30*"=")
    
    print_dir(output_path)
    
def del_dir(path):
    if not os.path.exists(path):
        return
    
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            del_dir(file_path)
        else:
            os.remove(file_path)
    os.rmdir(path)
    
def print_dir(path):
    if not os.path.exists(path):
        return
        
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            print_dir(file_path)
        else:
            print(file_path)

run_script(sys.argv[1])