//! URL parsing, output formatting, and filename building.
//! Ported from the Python `utils.py` / `core.py` formatting helpers.

use std::path::{Path, PathBuf};

use crate::youtube::{Metadata, Transcript};

pub const SEPARATOR: &str = "========================================================================";

/// One video's outcome: either the fetched data, or why it failed.
pub struct VideoResult {
    pub video_id: String,
    pub data: Result<(Metadata, Transcript), String>,
}

/// Extract a YouTube video ID from a URL or a bare ID.
///
/// Handles watch?v=, youtu.be/, /embed/, /shorts/, /live/, and bare 11-char IDs.
pub fn extract_video_id(raw: &str) -> Option<String> {
    let raw = raw.trim();

    // `v=` query parameter, in any position.
    if let Some(rest) = raw.split("v=").nth(1) {
        if let Some(id) = take_id(rest) {
            return Some(id);
        }
    }
    for marker in ["youtu.be/", "/embed/", "/shorts/", "/live/"] {
        if let Some(rest) = raw.split(marker).nth(1) {
            if let Some(id) = take_id(rest) {
                return Some(id);
            }
        }
    }
    // A bare ID — only if the whole string is one, so stray words are not accepted.
    take_id(raw).filter(|id| id.len() == raw.len())
}

/// Read an 11-character video ID from the front of `s`, if one is there.
fn take_id(s: &str) -> Option<String> {
    let id: String = s
        .chars()
        .take_while(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
        .collect();
    (id.len() == 11).then_some(id)
}

/// Parse multiline input into video IDs, skipping blanks, `#` comments, and duplicates.
/// Returns the IDs plus any lines that could not be parsed.
pub fn parse_url_list(text: &str) -> (Vec<String>, Vec<String>) {
    let mut ids: Vec<String> = Vec::new();
    let mut invalid: Vec<String> = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        match extract_video_id(line) {
            Some(id) if !ids.contains(&id) => ids.push(id),
            Some(_) => {} // duplicate
            None => invalid.push(line.to_string()),
        }
    }
    (ids, invalid)
}

/// Strip characters that are invalid in Windows filenames and cap the length.
pub fn sanitize_filename(name: &str) -> String {
    let cleaned: String = name
        .chars()
        .filter(|c| {
            !matches!(c, '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*') && !c.is_control()
        })
        .collect();
    let cleaned = cleaned.trim_matches(|c: char| c == '.' || c == ' ');
    let capped = truncate_chars(cleaned, 100);
    if capped.is_empty() { "transcript".to_string() } else { capped }
}

/// Truncate to at most `max` characters (not bytes, so multi-byte titles survive).
fn truncate_chars(s: &str, max: usize) -> String {
    s.chars().take(max).collect::<String>().trim_end().to_string()
}

pub fn format_timestamp(seconds: f64) -> String {
    let total = seconds as u64;
    format!("[{:02}:{:02}:{:02}]", total / 3600, (total % 3600) / 60, total % 60)
}

/// Build the descriptive output filename, mirroring the Python behaviour.
pub fn build_output_filename(results: &[VideoResult]) -> String {
    let titles: Vec<&str> = results
        .iter()
        .filter_map(|r| r.data.as_ref().ok().map(|(m, _)| m.title.as_str()))
        .collect();
    let mut dates: Vec<&str> = results
        .iter()
        .filter_map(|r| r.data.as_ref().ok().map(|(m, _)| m.upload_date.as_str()))
        .filter(|d| !d.is_empty())
        .collect();

    let first_date = dates.first().copied().unwrap_or("unknown");
    match titles.len() {
        0 => "transcripts.txt".to_string(),
        1 => format!("{}_{}.txt", sanitize_filename(titles[0]), first_date),
        2 => format!(
            "{}_and_{}_{}.txt",
            truncate_chars(&sanitize_filename(titles[0]), 40),
            truncate_chars(&sanitize_filename(titles[1]), 40),
            first_date,
        ),
        count => {
            dates.sort_unstable();
            let range = match (dates.first(), dates.last()) {
                (Some(a), Some(b)) => format!("{a}_to_{b}"),
                _ => "unknown".to_string(),
            };
            format!(
                "{}_and_{}_more_{}.txt",
                truncate_chars(&sanitize_filename(titles[0]), 50),
                count - 1,
                range,
            )
        }
    }
}

/// If `path` is taken, append `_1`, `_2`, ... until it is not.
pub fn ensure_unique_path(path: PathBuf) -> PathBuf {
    if !path.exists() {
        return path;
    }
    let stem = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
    let ext = path
        .extension()
        .map(|e| format!(".{}", e.to_string_lossy()))
        .unwrap_or_default();
    let parent = path.parent().unwrap_or(Path::new(".")).to_path_buf();
    for n in 1.. {
        let candidate = parent.join(format!("{stem}_{n}{ext}"));
        if !candidate.exists() {
            return candidate;
        }
    }
    unreachable!()
}

/// Render the complete output file.
pub fn render(results: &[VideoResult], include_timestamps: bool) -> String {
    let total = results.len();
    let ok = results.iter().filter(|r| r.data.is_ok()).count();

    let mut out = String::new();
    out.push_str(SEPARATOR);
    out.push_str("\n  VANSCRIPT — YouTube Transcripts\n");
    out.push_str(&format!("  {ok} of {total} video(s) transcribed successfully\n"));
    out.push_str(SEPARATOR);
    out.push('\n');

    // Sections are joined, not concatenated: the separating newline is what puts a
    // blank line between one video's last caption and the next video's header.
    let sections: Vec<String> = results
        .iter()
        .enumerate()
        .map(|(i, result)| render_section(result, i + 1, total, include_timestamps))
        .collect();
    out.push_str(&sections.join("\n"));
    out
}

/// Render one video's section: a header block, then its lines or its failure reason.
fn render_section(
    result: &VideoResult,
    index: usize,
    total: usize,
    include_timestamps: bool,
) -> String {
    let mut out = format!("\n{SEPARATOR}\n  VIDEO {index} of {total}\n{SEPARATOR}\n");
    match &result.data {
        Ok((meta, transcript)) => {
            out.push_str(&format!("  Title:    {}\n", meta.title));
            out.push_str(&format!("  Channel:  {}\n", meta.channel));
            out.push_str(&format!("  Date:     {}\n", meta.upload_date));
            out.push_str(&format!("  URL:      {}\n", meta.url));
            out.push_str(&format!("  Language: {}\n", transcript.language));
            out.push_str(&format!("  Lines:    {}\n", transcript.snippets.len()));
            out.push_str(SEPARATOR);
            out.push_str("\n\n");
            for snippet in &transcript.snippets {
                if include_timestamps {
                    out.push_str(&format_timestamp(snippet.start));
                    out.push(' ');
                }
                out.push_str(&snippet.text);
                out.push('\n');
            }
        }
        Err(error) => {
            out.push_str(&format!("  Video ID: {}\n", result.video_id));
            out.push_str("  Status:   FAILED\n");
            out.push_str(SEPARATOR);
            out.push_str("\n\n");
            out.push_str(&format!("[Transcript unavailable: {error}]\n"));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::youtube::Snippet;

    #[test]
    fn extracts_ids_from_every_url_shape() {
        for url in [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?si=xyz",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/live/dQw4w9WgXcQ",
            "dQw4w9WgXcQ",
        ] {
            assert_eq!(
                extract_video_id(url).as_deref(),
                Some("dQw4w9WgXcQ"),
                "failed on {url}"
            );
        }
    }

    #[test]
    fn rejects_non_urls() {
        assert_eq!(extract_video_id("hello world"), None);
        assert_eq!(extract_video_id("tooshort"), None);
        // 11 valid chars embedded in a longer word is not a bare ID.
        assert_eq!(extract_video_id("dQw4w9WgXcQextra"), None);
        assert_eq!(extract_video_id(""), None);
    }

    #[test]
    fn parses_lists_skipping_comments_and_duplicates() {
        let (ids, invalid) = parse_url_list(
            "\n# a comment\nhttps://youtu.be/dQw4w9WgXcQ\ndQw4w9WgXcQ\njNQXAC9IVRw\ngarbage line\n",
        );
        assert_eq!(ids, vec!["dQw4w9WgXcQ", "jNQXAC9IVRw"]);
        assert_eq!(invalid, vec!["garbage line"]);
    }

    #[test]
    fn sanitizes_filenames() {
        assert_eq!(sanitize_filename("a/b:c?d"), "abcd");
        assert_eq!(sanitize_filename("  ...  "), "transcript");
        assert_eq!(sanitize_filename("Ñandú — ok"), "Ñandú — ok");
        assert_eq!(sanitize_filename(&"x".repeat(200)).chars().count(), 100);
    }

    #[test]
    fn formats_timestamps() {
        assert_eq!(format_timestamp(0.0), "[00:00:00]");
        assert_eq!(format_timestamp(3661.9), "[01:01:01]");
        assert_eq!(format_timestamp(86399.0), "[23:59:59]");
    }

    fn stub(title: &str, date: &str) -> VideoResult {
        VideoResult {
            video_id: "x".into(),
            data: Ok((
                Metadata {
                    title: title.into(),
                    channel: "c".into(),
                    upload_date: date.into(),
                    url: "u".into(),
                },
                Transcript { language: "en".into(), snippets: vec![] },
            )),
        }
    }

    #[test]
    fn builds_filenames_by_video_count() {
        assert_eq!(build_output_filename(&[]), "transcripts.txt");
        assert_eq!(
            build_output_filename(&[stub("One", "2020-01-01")]),
            "One_2020-01-01.txt"
        );
        assert_eq!(
            build_output_filename(&[stub("One", "2020-01-01"), stub("Two", "2021-01-01")]),
            "One_and_Two_2020-01-01.txt",
        );
        assert_eq!(
            build_output_filename(&[
                stub("One", "2022-01-01"),
                stub("Two", "2020-01-01"),
                stub("Three", "2021-01-01"),
            ]),
            "One_and_2_more_2020-01-01_to_2022-01-01.txt",
        );
    }

    #[test]
    fn renders_failures_without_losing_successes() {
        let results = vec![
            VideoResult {
                video_id: "ok1".into(),
                data: Ok((
                    Metadata {
                        title: "Good".into(),
                        channel: "Chan".into(),
                        upload_date: "2020-01-01".into(),
                        url: "https://x".into(),
                    },
                    Transcript {
                        language: "English (en)".into(),
                        snippets: vec![Snippet { text: "hello".into(), start: 61.0 }],
                    },
                )),
            },
            VideoResult { video_id: "bad1".into(), data: Err("no transcript".into()) },
        ];
        let text = render(&results, true);
        assert!(text.contains("1 of 2 video(s) transcribed successfully"));
        assert!(text.contains("[00:01:01] hello"));
        assert!(text.contains("[Transcript unavailable: no transcript]"));
        // Without timestamps the text is bare.
        assert!(render(&results, false).contains("\nhello\n"));
    }
}
