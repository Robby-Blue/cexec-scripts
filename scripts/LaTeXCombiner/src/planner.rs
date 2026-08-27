use std::path::{Path, PathBuf};

use crate::{Document, Section};

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
        Element::TitlePage(title_page.title.clone())
    } else {
        Element::TitlePage(
            doc.path
                .file_name()
                .expect("name")
                .to_string_lossy()
                .into_owned(),
        )
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

#[derive(Debug)]
pub struct NestedElement {
    pub nesting: u8,
    pub element: Element,
}

#[derive(Debug)]
pub enum Element {
    TitlePage(String),
    LaTeXInclude(PathBuf),
}
