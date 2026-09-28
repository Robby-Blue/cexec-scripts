use chrono::DateTime;
use std::collections::HashMap;
use std::path::Path;
use std::{fs, io::Error};

use crate::planner::{CommitInfo, Element};
use crate::planner::{Plan, TitlePage};

pub fn combine(plan: &Plan, base_path: &Path, output_path: &Path) -> Result<(), Error> {
    fs::create_dir_all(output_path)?;

    let base_release_globals = base_path.join("globals").join("release");
    let output_release_globals = output_path.join("globals").join("release");
    copy_folder(&base_release_globals, &output_release_globals)?;

    let mut packages: HashMap<String, String> = HashMap::new();
    packages.insert(
        "globals/release/main".to_string(),
        "\\usepackage{globals/release/main}".to_string(),
    );
    let (new_packages, contents_str) = process_documents(plan, base_path, output_path)?;
    packages.extend(new_packages);

    let main_src = process_main_tex(&packages, &plan.globals, &contents_str, &plan.commit);
    let output_main = output_path.join("main.tex");
    fs::write(output_main, &main_src)?;

    Ok(())
}

fn process_main_tex(
    packages: &HashMap<String, String>,
    globals: &HashMap<String, String>,
    contents_str: &String,
    commit: &CommitInfo,
) -> String {
    let mut src = include_str!("template.tex").to_string();

    let mut packages_str = String::new();
    for (_, line) in packages {
        packages_str += &(line.to_owned() + "\n");
    }
    src = src.replace("<packages>", &packages_str);

    let mut globals_str = String::new();
    for (key, value) in globals {
        globals_str += &(format!("\\def\\zccglobal{key}{{{value}}}\n"));
    }

    let hash = &commit.hash;
    let datetime = DateTime::from_timestamp(commit.timestamp, 0).expect("bad timestamp");
    let date_str = datetime.format("%d.%m.%Y").to_string();
    globals_str += &(format!("\\def\\zcctitlepageeditdate{{{date_str}}}"));
    globals_str += &(format!("\\def\\zcctitlepagecommit{{{hash}}}"));
    src = src.replace("<globals>", &globals_str);

    src = src.replace("<contents>", &contents_str);

    src
}

fn process_documents(
    plan: &Plan,
    base_path: &Path,
    output_path: &Path,
) -> Result<(HashMap<String, String>, String), Error> {
    let mut packages: HashMap<String, String> = HashMap::new();
    let mut contents_str = String::new();

    let layer = plan.title_path.len() - 1;
    for e in plan.elements.iter() {
        let new_content = match &e.element {
            Element::TitlePage(titlepage) => {
                titlepage_to_latex(titlepage, layer, e.nesting as usize)
            }
            Element::LaTeXInclude(path) => {
                let relative_folder = path.strip_prefix(base_path).unwrap();
                let relative_folder = Path::new("repo").join(relative_folder);
                let main_path = relative_folder.join("main.tex");

                let main_path_str = main_path.to_str().expect("bad path");

                let output_folder = output_path.join(&relative_folder);

                let res = copy_section(path, &output_folder, e.nesting, layer)?;

                for (name, line) in res.packages {
                    if name.starts_with("/") {
                        continue;
                    }

                    if let Some(current_line) = packages.get(&name) {
                        if current_line != &line {
                            panic!("bad packages `{current_line}` and `{line}`")
                        }
                    }
                    packages.insert(name, line);
                }

                format!("\\input{{{main_path_str}}}").to_string()
            }
        };

        contents_str = contents_str + new_content.as_str() + "\n";
    }

    Ok((packages, contents_str))
}

fn titlepage_to_latex(titlepage: &TitlePage, layer: usize, nesting: usize) -> String {
    let title = titlepage.title.clone();

    let layer_subs = "sub".repeat(layer);
    let subs = "sub".repeat(nesting);

    let mut src = String::new();

    for (key, value) in titlepage.args.iter() {
        src += &format!("\\def\\zcc{subs}titlepage{key}{{{value}}}");
    }

    src += &format!("\\zc{layer_subs}layer{subs}section{{{title}}}");

    src
}

fn copy_section(
    input_folder: &Path,
    output_folder: &Path,
    nesting: u8,
    layer: usize,
) -> Result<SectionResult, Error> {
    copy_folder(input_folder, output_folder)?;

    let main_path = input_folder.join("main.tex");

    let main_src = fs::read_to_string(main_path)?;
    let (new_main_src, res) = rewrite_main(main_src, nesting, layer);

    fs::create_dir_all(output_folder)?;
    let new_main_path = output_folder.join("main.tex");

    fs::write(new_main_path, new_main_src)?;

    Ok(res)
}

fn rewrite_main(mut src: String, nesting: u8, layer: usize) -> (String, SectionResult) {
    src = src.replace("\\documentclass{article}", "");
    src = src.replace("\\begin{document}", "");
    src = src.replace("\\end{document}", "");

    let (mut src, packages) = remove_packages(src);

    src = replace_sections(src, nesting, 0, layer);
    src = replace_sections(src, nesting, 1, layer);
    src = replace_sections(src, nesting, 2, layer);

    src = delete_commmands(src);

    let res = SectionResult::new(packages);
    (src, res)
}

fn remove_packages(mut src: String) -> (String, HashMap<String, String>) {
    let mut packages = HashMap::new();
    while src.contains("\\usepackage") {
        let line_start_index = src.find("\\usepackage").unwrap();
        let line_end_index = line_start_index + src[line_start_index..].find("\n").unwrap();

        let line = &src[line_start_index..line_end_index].trim();

        let package_start_index = line.find("{").unwrap() + 1;
        let package_end_index = line.find("}").unwrap();

        let package_name = &line[package_start_index..package_end_index];

        packages.insert(package_name.to_string(), line.to_string());

        src = src.replace(line, "");
    }

    (src, packages)
}

fn replace_sections(src: String, doc_nesting: u8, nesting: u8, layer: usize) -> String {
    let original_subs = "sub".repeat(nesting as usize);
    let original = format!("\\{original_subs}section{{");

    let layer_subs = "sub".repeat(layer);
    let new_subs = "sub".repeat((doc_nesting + nesting) as usize);
    let new = format!("\\zc{layer_subs}layer{new_subs}section{{");

    src.replace(&original, &new)
}

fn delete_commmands(mut src: String) -> String {
    for (i, _) in src.clone().match_indices("\\newcommand") {
        let command_start_index = src[i + 1..].find("\\").unwrap() + i + 2;
        let command_end_index = src[i..].find("}").unwrap() + i;

        let command_name = &src[command_start_index..command_end_index];

        src += &format!("\\let\\{command_name}\\undefined\n");
    }

    src
}

fn copy_folder(source_path: &Path, destination_path: &Path) -> Result<(), Error> {
    fs::create_dir_all(destination_path)?;

    for entry in fs::read_dir(source_path)? {
        let entry = entry?;
        let source_entry_path = entry.path();
        let destination_entry_path = destination_path.join(entry.file_name());

        let file_type = entry.file_type()?;
        if file_type.is_dir() {
            copy_folder(&source_entry_path, &destination_entry_path)?;
        } else {
            fs::copy(&source_entry_path, &destination_entry_path)?;
        }
    }

    Ok(())
}

struct SectionResult {
    packages: HashMap<String, String>,
}

impl SectionResult {
    fn new(packages: HashMap<String, String>) -> Self {
        SectionResult { packages }
    }
}
