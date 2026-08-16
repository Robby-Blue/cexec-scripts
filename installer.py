from datetime import datetime
import argparse
import subprocess
import shutil
import os
import json

def install_scripts(source_path, destination_path, device):
    source_scripts_path = os.path.join(source_path, "scripts")
    destination_scripts_path = os.path.join(destination_path, "scripts")
    
    source_scripts = os.listdir(source_scripts_path)
    destination_scripts = os.listdir(destination_scripts_path)
  
    for script in source_scripts:
        already_exists = script in destination_scripts

        source_script_path = os.path.join(source_scripts_path, script)
        
        script_config = read_script_config(source_script_path)
        supported_devices = script_config.get("devices", [])
        
        device_is_supported = device in supported_devices
        
        should_copy = already_exists or device_is_supported

        if not should_copy:
            continue

        destination_script_path = os.path.join(destination_scripts_path, script)
        os.makedirs(destination_script_path, exist_ok=True)
        
        copy_folder(source_script_path, destination_script_path)

def read_script_config(script_path):
    script_config_path = os.path.join(script_path, "config.json")
    with open(script_config_path, "r") as f:
        return json.load(f)

def copy_folder(source_path, destination_path):    
    source_files = os.listdir(source_path)
    destination_files = os.listdir(destination_path)
    
    for destination_file in destination_files:
        if destination_file in source_files:
            continue
        destination_file_path = os.path.join(destination_path, destination_file)
        delete(destination_file_path)

    for source_file in source_files:
        source_file_path = os.path.join(source_path, source_file)
        destination_file_path = os.path.join(destination_path, source_file)

        if not needs_to_copy(source_file_path, destination_file_path):
            continue

        if os.path.isdir(destination_file_path):
            copy_folder(source_file_path, destination_file_path)
        else:
            shutil.copy(source_file_path, destination_file_path)

def needs_to_copy(source, destination):
    if not os.path.exists(destination):
        return True
    
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", source],
        capture_output=True, text=True, check=True
    )
    iso_str = result.stdout.strip()
    if not iso_str:
        return None
    source_edit_time = datetime.fromisoformat(iso_str).replace(tzinfo=None)
    
    destination_edit_time_unix = os.path.getmtime(destination)
    destination_edit_time = datetime.fromtimestamp(destination_edit_time_unix)
    
    return source_edit_time > destination_edit_time 

def delete(path):
    if os.path.isdir(path):
        for file in os.listdir(path):
            file_path = os.path.join(file, path)
            delete(file_path)
        os.rmdir(path)
    else:
        os.remove(path)

parser = argparse.ArgumentParser()

parser.add_argument('-i', '--source_folder', default=".")
parser.add_argument('-o', '--destination_folder', default="..")
parser.add_argument('-a', '--auto', action='store_true')
parser.add_argument('-d', '--device')
parser.add_argument('-b', '--build', action='store_true')

args = parser.parse_args()

if not args.auto:
    print("manual not supported yet")
    exit(1)

if args.build:
    print("build not supported yet")
    exit(1)

install_scripts(args.source_folder, args.destination_folder,
    args.device)