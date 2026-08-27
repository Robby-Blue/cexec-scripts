use std::ffi::OsStr;
use std::path::Path;
use std::path::PathBuf;

use glp::CustomParser;
use glp::ParseContext;
use glp::Stream;
use glp::errors::ParseError;
use glp::parser::nodes::Expression;
use glp::parser::nodes::FuncCall;
use glp::parser::nodes::Value;
use glp::tokenizer::Token;

use std::fs;

use crate::Document;
use crate::Section;
use crate::TitlePage;

pub fn parse_structure(folder_path: &Path) -> Result<Document, ParseError> {
    let file_path = folder_path.join("structure").join("structure.str");

    if !file_path.exists() {
        let parts = fill_missing_parts(vec![], folder_path)?;

        return Ok(Document::new(folder_path.into(), None, parts));
    }

    let custom = StructureParser {};
    let ctx = ParseContext::new(custom);

    let root_doc = glp::parse_file(&file_path.to_string_lossy().to_string(), &ctx)?;

    let ctx = StructureContext::new(folder_path);

    Ok(parse_document(&root_doc, &ctx)?)
}

fn parse_document(
    doc_call: &FuncCall<StructureParser>,
    ctx: &StructureContext,
) -> Result<Document, ParseError> {
    if &doc_call.name.text != "document" {
        return Err(ParseError::new("expected doc"));
    }

    let title_page = match allow_call(doc_call.kwargs.get("titlepage"))? {
        Some(f) => Some(parse_title_page(&f, ctx)?),
        None => None,
    };

    let auto_add_docs = match allow_bool(doc_call.kwargs.get("auto_add_docs"))? {
        Some(f) => f,
        None => true,
    };

    let mut parts = vec![];
    for call in doc_call.funcs.iter() {
        let part = parse_part(call, ctx)?;
        parts.push(part);
    }

    if auto_add_docs {
        parts = fill_missing_parts(parts, &ctx.folder_path)?;
    }

    let pathbuf = ctx.folder_path.clone().into();
    Ok(Document::new(pathbuf, title_page, parts))
}

fn parse_title_page(
    title_page_call: &FuncCall<StructureParser>,
    _ctx: &StructureContext,
) -> Result<TitlePage, ParseError> {
    if &title_page_call.name.text != "titlepage" {
        return Err(ParseError::new("expected titlepage call"));
    }

    let title = expect_string(title_page_call.kwargs.get("title"), "title")?;

    Ok(TitlePage { title })
}

fn parse_part(
    call: &FuncCall<StructureParser>,
    ctx: &StructureContext,
) -> Result<Section, ParseError> {
    match call.name.text.as_str() {
        "use_doc" => Ok(parse_use_doc(call, ctx)?),
        "use_sec" => Ok(parse_use_sec(call, ctx)?),
        _ => Err(ParseError::new(
            format!("wrong name {}", call.name.text).as_str(),
        )),
    }
}

fn parse_use_doc(
    call: &FuncCall<StructureParser>,
    ctx: &StructureContext,
) -> Result<Section, ParseError> {
    let path = expect_string(call.kwargs.get("path"), "path")?;

    let doc_folder_path = ctx.folder_path.join(&path);

    let doc = parse_structure(&doc_folder_path)?;

    Ok(Section::Document(doc))
}

fn parse_use_sec(
    call: &FuncCall<StructureParser>,
    ctx: &StructureContext,
) -> Result<Section, ParseError> {
    let name = expect_string(call.args.get(0), "first")?;

    let path = ctx.folder_path.join(name);

    Ok(Section::Section(PathBuf::from(path)))
}

pub fn fill_missing_parts(
    mut parts: Vec<Section>,
    base_path: &Path,
) -> Result<Vec<Section>, ParseError> {
    let children = fs::read_dir(base_path).expect("section is not a real section");

    let paths: Vec<PathBuf> = parts
        .iter()
        .map(|p| match p {
            Section::Document(doc) => doc.path.clone(),
            Section::Section(path) => path.clone(),
        })
        .collect();
    let names: Vec<&OsStr> = paths
        .iter()
        .filter_map(|child_path| {
            let relative_path = child_path.strip_prefix(base_path);
            let folder_name = relative_path.unwrap().iter().next();

            folder_name
        })
        .collect();
    // we get the first part of the name, because if you
    // include a/b/, we dont want to reinclude a/

    for child in children {
        let child = child.expect("file disappeared :(");
        let child_path = child.path();

        if !child_path.is_dir() {
            continue;
        }

        // only if it isnt already included!!!!
        if names.contains(&child.file_name().as_os_str()) {
            continue;
        }
        if child.file_name() == "structure" {
            continue;
        }
        if child.file_name() == "globals" {
            continue;
        }
        if child.file_name() == ".git" {
            continue;
        }

        let main_tex_path = child_path.join("main.tex");

        if main_tex_path.exists() {
            parts.push(Section::Section(child_path));
        } else {
            let doc = parse_structure(&child_path)?;
            parts.push(Section::Document(doc));
        }
    }

    Ok(parts)
}

pub fn expect_string(
    expr: Option<&Box<Expression<StructureParser>>>,
    name: &str,
) -> Result<String, ParseError> {
    let expr = match expr {
        Some(expr) => *expr.clone(),
        None => {
            return Err(ParseError::new(
                &format!("arg {name} not found").to_string(),
            ));
        }
    };

    let str = match expr {
        Expression::Value(Value::String(f)) => f,
        _ => return Err(ParseError::new("expected string")),
    };
    Ok(str)
}

pub fn allow_call(
    expr: Option<&Box<Expression<StructureParser>>>,
) -> Result<Option<FuncCall<StructureParser>>, ParseError> {
    let expr = match expr {
        Some(expr) => *expr.clone(),
        None => return Ok(None),
    };

    let f = match expr {
        Expression::Value(Value::FuncCall(f)) => *f,
        _ => return Err(ParseError::new("expected string")),
    };
    Ok(Some(f))
}

pub fn allow_bool(
    expr: Option<&Box<Expression<StructureParser>>>,
) -> Result<Option<bool>, ParseError> {
    let expr = match expr {
        Some(expr) => *expr.clone(),
        None => return Ok(None),
    };

    let f = match expr {
        Expression::Value(Value::Bool(f)) => f,
        _ => return Err(ParseError::new("expected bool")),
    };
    Ok(Some(f))
}

struct StructureContext {
    folder_path: PathBuf,
}

impl StructureContext {
    pub fn new(folder_path: impl Into<PathBuf>) -> Self {
        StructureContext {
            folder_path: folder_path.into(),
        }
    }
}

#[derive(Clone)]
pub enum NoTokens {}

#[derive(Clone)]
pub enum NoValues {}

#[derive(Clone)]
pub enum NoUnits {}

#[derive(Clone)]
pub struct StructureParser;

impl CustomParser for StructureParser {
    type Token = NoTokens;
    type Value = NoValues;
    type Unit = NoUnits;

    fn get_custom_keywords(&self) -> Vec<String> {
        vec![]
    }

    fn parse_token(&self, _stream: &mut Stream<char>) -> Result<Option<Self::Token>, ParseError> {
        Ok(None)
    }

    fn parse_value(
        &self,
        _stream: &mut Stream<Token<Self>>,
    ) -> Result<Option<NoValues>, ParseError> {
        Ok(None)
    }

    fn parse_unit(&self, _stream: &mut Stream<Token<Self>>) -> Result<Option<NoUnits>, ParseError> {
        Ok(None)
    }
}
