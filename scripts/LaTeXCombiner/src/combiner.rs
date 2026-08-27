use std::collections::HashMap;
use std::path::Path;
use std::{fs, io::Error};

use crate::planner::{Element, NestedElement};

pub fn combine(
    plan: &Vec<NestedElement>,
    base_path: &Path,
    output_path: &Path,
) -> Result<(), Error> {
    fs::create_dir_all(output_path)?;

    let mut contents_str = String::new();
    let mut packages: HashMap<String, String> = HashMap::new();

    packages.insert(
        "globals/release/main".to_string(),
        "\\usepackage{globals/release/main}".to_string(),
    );

    let base_release_globals = base_path.join("globals").join("release");
    let output_release_globals = output_path.join("globals").join("release");

    copy_folder(&base_release_globals, &output_release_globals)?;

    for e in plan {
        let new_content = match &e.element {
            Element::TitlePage(title) => {
                let subs = "sub".repeat(e.nesting as usize);
                format!("\\zc{subs}section{{{title}}}").to_string()
            }
            Element::LaTeXInclude(path) => {
                let relative_folder = path.strip_prefix(base_path).unwrap();
                let relative_folder = Path::new("repo").join(relative_folder);
                let main_path = relative_folder.join("main.tex");

                let main_path_str = main_path.to_str().expect("bad path");

                let output_folder = output_path.join(&relative_folder);

                let res = copy_section(path, &output_folder, e.nesting)?;

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

    let mut packages_str = String::new();
    for (_, line) in packages {
        packages_str = packages_str + line.as_str() + "\n";
    }

    let template = include_str!("template.tex");
    let template = template.replace("<contents>", &contents_str);
    let template = template.replace("<packages>", &packages_str);

    let output_main = output_path.join("main.tex");
    fs::write(output_main, &template)?;

    Ok(())
}

fn copy_section(
    input_folder: &Path,
    output_folder: &Path,
    nesting: u8,
) -> Result<SectionResult, Error> {
    copy_folder(input_folder, output_folder)?;

    let main_path = input_folder.join("main.tex");

    let main_src = fs::read_to_string(main_path)?;
    let (new_main_src, res) = rewrite_main(main_src, nesting);

    fs::create_dir_all(output_folder)?;
    let new_main_path = output_folder.join("main.tex");

    fs::write(new_main_path, new_main_src)?;

    Ok(res)
}

fn rewrite_main(mut src: String, nesting: u8) -> (String, SectionResult) {
    src = src.replace("\\documentclass{article}", "");
    src = src.replace("\\begin{document}", "");
    src = src.replace("\\end{document}", "");

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

    src = replace_sections(src, nesting, 0);
    src = replace_sections(src, nesting, 1);
    src = replace_sections(src, nesting, 2);

    let res = SectionResult::new(packages);
    (src, res)
}

fn replace_sections(src: String, doc_nesting: u8, nesting: u8) -> String {
    let original_subs = "sub".repeat(nesting as usize);
    let original = format!("\\{original_subs}section{{");

    let new_subs = "sub".repeat((doc_nesting + nesting) as usize);
    let new = format!("\\zc{new_subs}section{{");

    src.replace(&original, &new)
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
