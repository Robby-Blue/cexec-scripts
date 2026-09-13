use crate::planner::NestedElement;
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    fs,
    path::{Path, PathBuf},
};

mod combiner;
mod parser;
mod planner;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = Path::new("/app/workspace/repo");
    let structure = parser::parse_structure(path)?;
    println!("Parsed structure");
    println!("{structure:#?}");

    let globals = structure.globals.clone();
    let plans = walk_document(&structure, &globals, vec![]);
    println!("Created {} plans", plans.iter().count());

    for (i, plan) in plans.iter().enumerate() {
        println!("Writing plan {i}");
        println!("{plan:#?}");
        let output_path = Path::new("/app/output/run").join(i.to_string());

        combiner::combine(&plan, path, &output_path)?;
    }
    println!("Wrote plans");

    let output_json = get_output_json(&plans);
    let json_string = serde_json::to_string_pretty(&output_json)?;
    fs::write("/app/output/output.json", json_string)?;
    println!("Wrote output.json");

    Ok(())
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

fn walk_document(
    doc: &Document,
    globals: &HashMap<String, String>,
    mut title_path: Vec<String>,
) -> Vec<Plan> {
    let mut plans = vec![];

    let elements = planner::plan_document(&doc);

    let title = get_title_from_elements(&elements);
    title_path.push(title);

    let plan = Plan {
        title_path: title_path.clone(),
        globals: globals.clone(),
        elements,
    };
    plans.push(plan);

    let iter = doc.parts.iter();
    for part in iter {
        match &**part {
            Section::Document(document) => {
                plans.append(&mut walk_document(&document, globals, title_path.clone()))
            }
            Section::Section(section_path) => {
                let elements = planner::plan_section(&section_path);

                let title = get_title_from_elements(&elements);
                let mut new_title_path = title_path.clone();
                new_title_path.push(title);

                let plan = Plan {
                    title_path: new_title_path,
                    globals: globals.clone(),
                    elements,
                };

                plans.push(plan)
            }
        }
    }

    plans
}

fn get_title_from_elements(elements: &Vec<NestedElement>) -> String {
    let element = elements.first().unwrap();
    let title = match &element.element {
        planner::Element::TitlePage(titlepage) => titlepage.title.clone(),
        planner::Element::LaTeXInclude(path) => path
            .file_name()
            .expect("bad name")
            .to_string_lossy()
            .to_string(),
    };

    title.replace(" ", "_").to_lowercase()
}

#[derive(Debug)]
struct Plan {
    pub globals: HashMap<String, String>,
    pub title_path: Vec<String>,
    pub elements: Vec<NestedElement>,
}

#[derive(Clone, Debug)]
struct TitlePage {
    pub title: String,
    pub args: HashMap<String, String>,
}

#[derive(Debug)]
enum Section {
    Document(Document),
    Section(PathBuf),
}

#[derive(Debug)]
struct Document {
    pub path: PathBuf,
    pub globals: HashMap<String, String>,
    pub title_page: Option<TitlePage>,
    pub parts: Vec<Box<Section>>,
}
impl Document {
    pub fn new(
        path: PathBuf,
        globals: HashMap<String, String>,
        title_page: Option<TitlePage>,
        parts: Vec<Section>,
    ) -> Self {
        let parts = parts.into_iter().map(|p| Box::new(p)).collect();

        Document {
            path,
            globals,
            title_page,
            parts,
        }
    }
}
