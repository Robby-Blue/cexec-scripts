from datetime import datetime
import argparse
import subprocess
import shutil
import os

def install_scripts(source_path, destination_path):
    source_scripts_path = os.path.join(source_path, "scripts")
    destination_scripts_path = os.path.join(destination_path, "scripts")
    
    source_scripts = os.listdir(source_scripts_path)
    destination_scripts = os.listdir(destination_scripts_path)
  
    for script in source_scripts:
        if script not in destination_scripts:
            continue
        source_script_path = os.path.join(source_scripts_path, script)
        destination_script_path = os.path.join(destination_scripts_path, script)
            
        copy_folder(source_script_path, destination_script_path)

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

parser.add_argument('-a', '--auto', action='store_true')
parser.add_argument('-b', '--build', action='store_true')
parser.add_argument('-i', '--source_folder', default=".")
parser.add_argument('-o', '--destination_folder', default="..")

args = parser.parse_args()

if not args.auto:
    print("manual not supported yet")
    exit(1)

if args.build:
    print("build not supported yet")
    exit(1)

install_scripts(args.source_folder, args.destination_folder)