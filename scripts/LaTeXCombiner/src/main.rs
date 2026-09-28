use serde_json::{Value, json};
use std::{collections::HashMap, fs, path::Path};

mod combiner;
mod parser;
mod planner;

use crate::planner::{CommitInfo, Plan};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = Path::new("/app/input/repo");
    let structure = parser::parse_structure(path)?;
    println!("Parsed structure");
    println!("{structure:#?}");

    let last_edits_path = Path::new("/app/input/git_file_edit_infos.json");
    let last_edits_str = fs::read_to_string(last_edits_path)?;
    let last_edit_times: HashMap<String, CommitInfo> =
        serde_json::from_str(last_edits_str.as_str())?;

    let planner = planner::Planner { last_edit_times };
    let globals = structure.globals.clone();
    let plans = planner.plan_structure(&structure, &globals);
    println!("Created {} plans", plans.iter().count());

    let last_builds_path = Path::new("/app/input/last_build_times.json");
    let mut last_builds: HashMap<String, i64> = if last_builds_path.exists() {
        let last_builds_str = fs::read_to_string(last_builds_path)?;
        serde_json::from_str(last_builds_str.as_str())?
    } else {
        HashMap::new()
    };

    let plans = filter_new_plans(plans, &last_builds);
    println!("{} new plans", plans.iter().count());

    for (i, plan) in plans.iter().enumerate() {
        println!("Writing plan {i}");
        println!("{plan:#?}");
        let output_path = Path::new("/app/output/run").join(i.to_string());

        combiner::combine(&plan, path, &output_path)?;
        last_builds.insert(plan.title_path.join("/"), plan.commit.timestamp);
    }
    println!("Wrote plans");

    let output_json = get_output_json(&plans);
    let json_string = serde_json::to_string_pretty(&output_json)?;
    fs::write("/app/output/output.json", json_string)?;
    println!("Wrote output.json");

    fs::create_dir_all("/app/output/global/LaTeX/")?;
    let last_builds_str = serde_json::to_string_pretty(&last_builds)?;
    fs::write(
        "/app/output/global/LaTeX/last_build_times.json",
        last_builds_str,
    )?;
    println!("Wrote last_build_times.json");

    Ok(())
}

fn filter_new_plans(plans: Vec<Plan>, last_builds: &HashMap<String, i64>) -> Vec<Plan> {
    plans
        .into_iter()
        .filter(|p| {
            let path_str = p.title_path.join("/");
            let last_build = last_builds.get(&path_str).unwrap_or(&0);

            last_build < &p.commit.timestamp
        })
        .collect()
}

fn get_output_json(plans: &Vec<Plan>) -> Value {
    let mut new_tasks = vec![];

    for (i, plan) in plans.iter().enumerate() {
        let repo_path = plan.title_path.join("_");
        let task_json = json! ({
            "script": "LaTeXCompiler",
            "tag": format!("LaTex_{repo_path}").to_owned(),
            "data": get_data_for_task(i, plan)
        });

        new_tasks.push(task_json);
    }

    json!({
        "new_tasks": new_tasks
    })
}

fn get_data_for_task(id: usize, plan: &Plan) -> Value {
    let repo_path = plan.title_path.join("/");
    let final_path = format!("global/LaTeX/{repo_path}.pdf").to_owned();

    json!({
        "vars": {
            "name": plan.title_path[0],
            "is_top_level_doc": plan.title_path.len() == 1
        },
        "input_files": [{
            "server": {
                "folder": "run",
                "run_id": "parent",
                "path": id.to_string()
            },
            "client": "repo"
        }],
        "output_files_map": [{
            "client": "run/main.pdf",
            "server": final_path,
        }],
    })
}
