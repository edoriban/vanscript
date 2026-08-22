// On Windows the app is GUI-first, and a console window flashing behind it reads as
// a bug — the Python build hid it too. Kept in debug builds so `println!` still works.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

//! VanScript — YouTube transcript downloader.
//!
//! Usage:
//!   vanscript-rs                          (launch the GUI)
//!   vanscript-rs [OPTIONS] <URL_OR_ID>...
//!   vanscript-rs [OPTIONS] --stdin        (read one URL per line)
//!
//! Options:
//!   -l, --lang <CODES>   Comma-separated language preference (default: es,en)
//!   -o, --out <DIR>      Output directory (default: ~/Downloads, else $HOME)
//!   -t, --timestamps     Prefix every line with [HH:MM:SS]
//!       --stdin          Read URLs from standard input
//!   -h, --help           Show this help

mod gui;
mod output;
mod youtube;

use std::io::Read;
use std::path::PathBuf;

use anyhow::{Result, bail};

use output::VideoResult;

const HELP: &str = "\
VanScript — YouTube transcript downloader

USAGE:
    vanscript-rs [OPTIONS] <URL_OR_ID>...
    vanscript-rs [OPTIONS] --stdin

OPTIONS:
    -l, --lang <CODES>   Comma-separated language preference (default: es,en)
    -o, --out <DIR>      Output directory (default: ~/Downloads, else $HOME)
    -t, --timestamps     Prefix every line with [HH:MM:SS]
        --stdin          Read URLs from standard input, one per line
    -h, --help           Show this help
";

struct Args {
    input: String,
    languages: Vec<String>,
    out_dir: PathBuf,
    timestamps: bool,
}

fn parse_args() -> Result<Option<Args>> {
    let mut languages = vec!["es".to_string(), "en".to_string()];
    let mut out_dir = default_downloads_dir();
    let mut timestamps = false;
    let mut from_stdin = false;
    let mut positional: Vec<String> = Vec::new();

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "-h" | "--help" => {
                print!("{HELP}");
                return Ok(None);
            }
            "-t" | "--timestamps" => timestamps = true,
            "--stdin" => from_stdin = true,
            "-l" | "--lang" => {
                let value = args.next().ok_or_else(|| anyhow::anyhow!("--lang needs a value"))?;
                languages = value
                    .split(',')
                    .map(|s| s.trim().to_lowercase())
                    .filter(|s| !s.is_empty())
                    .collect();
            }
            "-o" | "--out" => {
                let value = args.next().ok_or_else(|| anyhow::anyhow!("--out needs a value"))?;
                out_dir = PathBuf::from(value);
            }
            other if other.starts_with('-') => bail!("unknown option: {other}"),
            other => positional.push(other.to_string()),
        }
    }

    let input = if from_stdin {
        let mut buf = String::new();
        std::io::stdin().read_to_string(&mut buf)?;
        buf
    } else {
        positional.join("\n")
    };

    if input.trim().is_empty() {
        print!("{HELP}");
        return Ok(None);
    }
    Ok(Some(Args { input, languages, out_dir, timestamps }))
}

/// `~/Downloads` when it exists, otherwise the home directory.
fn default_downloads_dir() -> PathBuf {
    let home = std::env::var_os("HOME").map(PathBuf::from).unwrap_or_else(|| PathBuf::from("."));
    let downloads = home.join("Downloads");
    if downloads.is_dir() { downloads } else { home }
}

fn main() -> Result<()> {
    // No arguments at all means the user launched the app, not the CLI.
    if std::env::args().len() == 1 {
        gui::run(default_downloads_dir()).map_err(|e| anyhow::anyhow!("{e}"))?;
        return Ok(());
    }

    let Some(args) = parse_args()? else { return Ok(()) };

    let (ids, invalid) = output::parse_url_list(&args.input);
    for line in &invalid {
        eprintln!("skipped (not a YouTube URL): {line}");
    }
    if ids.is_empty() {
        bail!("no valid YouTube URLs found");
    }

    let client = youtube::Client::new()?;
    let total = ids.len();
    let mut results = Vec::with_capacity(total);

    // One failure never stops the rest — same guarantee as the Python version.
    for (i, id) in ids.iter().enumerate() {
        eprint!("[{}/{}] {id} ... ", i + 1, total);
        let data = client.fetch(id, &args.languages).map_err(|e| e.to_string());
        match &data {
            Ok((meta, transcript)) => {
                eprintln!("{} ({} lines)", meta.title, transcript.snippets.len())
            }
            Err(error) => eprintln!("FAILED: {error}"),
        }
        results.push(VideoResult { video_id: id.clone(), data });
    }

    let text = output::render(&results, args.timestamps);
    std::fs::create_dir_all(&args.out_dir)?;
    let path = output::ensure_unique_path(args.out_dir.join(output::build_output_filename(&results)));
    std::fs::write(&path, text)?;

    let ok = results.iter().filter(|r| r.data.is_ok()).count();
    println!("{ok}/{total} transcribed → {}", path.display());
    Ok(())
}
