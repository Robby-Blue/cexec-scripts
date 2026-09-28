use std::{
    collections::HashMap,
    path::{Path, PathBuf},
};

pub struct Planner {
    pub last_edit_times: HashMap<String, CommitInfo>,
}

impl Planner {
    pub fn plan_structure(&self, doc: &Document, globals: &HashMap<String, String>) -> Vec<Plan> {
        self.walk_document(doc, globals, vec![])
    }

    fn walk_document(
        &self,
        doc: &Document,
        globals: &HashMap<String, String>,
        mut title_path: Vec<String>,
    ) -> Vec<Plan> {
        let mut plans = vec![];

        let elements = plan_document(&doc);

        let title = get_title_from_elements(&elements);
        title_path.push(title);

        let plan = Plan {
            title_path: title_path.clone(),
            globals: globals.clone(),
            elements: elements.clone(),
            commit: self.get_commit(&elements),
        };
        plans.push(plan);

        let iter = doc.parts.iter();
        for part in iter {
            match &**part {
                Section::Document(document) => {
                    plans.append(&mut self.walk_document(&document, globals, title_path.clone()))
                }
                Section::Section(section_path) => {
                    let elements = plan_section(&section_path);

                    let title = get_title_from_elements(&elements);
                    let mut new_title_path = title_path.clone();
                    new_title_path.push(title);

                    let plan = Plan {
                        title_path: new_title_path,
                        globals: globals.clone(),
                        elements: elements.clone(),
                        commit: self.get_commit(&elements),
                    };

                    plans.push(plan)
                }
            }
        }

        plans
    }

    fn get_commit(&self, elements: &Vec<NestedElement>) -> CommitInfo {
        let repo_path = Path::new("/app/input/repo");

        let mut paths = vec![];
        for element in elements {
            let Element::LaTeXInclude(path) = &element.element else {
                continue;
            };

            let rel = path.strip_prefix(repo_path).expect("path out of repo");

            paths.push("./".to_string() + rel.to_str().expect("bad name"));
        }
        paths.push("./globals/release".to_string());

        let mut latest_commit: Option<CommitInfo> = None;

        for path in paths {
            let this_commit = self
                .last_edit_times
                .get(&path)
                .expect("folder not found in repo");

            if latest_commit.is_none()
                || this_commit.timestamp > latest_commit.clone().unwrap().timestamp
            {
                latest_commit = Some(this_commit.clone());
            }
        }

        let latest_commit = latest_commit.expect("no path found");
        latest_commit
    }
}

fn get_title_from_elements(elements: &Vec<NestedElement>) -> String {
    let element = elements.first().unwrap();
    let title = match &element.element {
        Element::TitlePage(titlepage) => titlepage.title.clone(),
        Element::LaTeXInclude(path) => path
            .file_name()
            .expect("bad name")
            .to_string_lossy()
            .to_string(),
    };

    title.replace(" ", "_").to_lowercase()
}

pub fn plan_document(doc: &Document) -> Vec<NestedElement> {
    flatten_document(doc, 0)
}

pub fn plan_section(path: &Path) -> Vec<NestedElement> {
    vec![plan_nested_section(path, 0)]
}

pub fn plan_nested_section(path: &Path, nesting: u8) -> NestedElement {
    let element = Element::LaTeXInclude(path.into());
    let nested_element = NestedElement { nesting, element };

    nested_element
}

fn flatten_document(doc: &Document, nesting: u8) -> Vec<NestedElement> {
    let mut elements = vec![];

    let title_element = if let Some(title_page) = &doc.title_page {
        Element::TitlePage(title_page.clone())
    } else {
        Element::TitlePage(TitlePage {
            title: doc
                .path
                .file_name()
                .expect("name")
                .to_string_lossy()
                .into_owned(),
            args: HashMap::new(),
        })
    };
    let nested_element = NestedElement {
        nesting,
        element: title_element,
    };

    elements.push(nested_element);

    let iter = doc.parts.iter();
    for part in iter {
        match &**part {
            Section::Document(document) => {
                let mut new_elements = flatten_document(&document, nesting + 1);
                elements.append(&mut new_elements);
            }
            Section::Section(path) => {
                let nested_element = plan_nested_section(path, nesting + 1);

                elements.push(nested_element);
            }
        }
    }

    elements
}

#[derive(Debug, Clone)]
pub struct NestedElement {
    pub nesting: u8,
    pub element: Element,
}

#[derive(Debug, Clone)]
pub enum Element {
    TitlePage(TitlePage),
    LaTeXInclude(PathBuf),
}

#[derive(Debug)]
pub struct Plan {
    pub globals: HashMap<String, String>,
    pub title_path: Vec<String>,
    pub elements: Vec<NestedElement>,
    pub commit: CommitInfo,
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct CommitInfo {
    pub hash: String,
    pub timestamp: i64,
}

#[derive(Clone, Debug)]
pub struct TitlePage {
    pub title: String,
    pub args: HashMap<String, String>,
}

#[derive(Debug)]
pub enum Section {
    Document(Document),
    Section(PathBuf),
}

#[derive(Debug)]
pub struct Document {
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
