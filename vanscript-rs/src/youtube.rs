//! Fetching video metadata and transcripts straight from YouTube's InnerTube API.
//!
//! This replaces both Python dependencies the original used:
//!   - yt-dlp                  -> metadata (title, channel, duration, upload date)
//!   - youtube-transcript-api  -> caption tracks and their text
//!
//! The recipe, which is what youtube-transcript-api does internally:
//!   1. GET the watch page once. Scrape `INNERTUBE_API_KEY` (it rotates, so it
//!      cannot be hardcoded) and `uploadDate` (absent from the ANDROID response).
//!   2. POST `youtubei/v1/player` with that key and an ANDROID client context.
//!      Caption baseUrls in that response work without a proof-of-origin token,
//!      which the ones on the watch page do not.
//!   3. GET the chosen track's baseUrl as json3.

use std::io::Read;
use std::net::{IpAddr, Ipv4Addr};
use std::sync::atomic::{AtomicBool, Ordering};

use anyhow::{Context, Result, anyhow, bail};
use serde_json::{Value, json};

const ANDROID_CLIENT_VERSION: &str = "20.10.38";
const USER_AGENT: &str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 \
                          (KHTML, like Gecko) Chrome/126.0 Safari/537.36";

/// Caps on what YouTube is allowed to hand back. These are trust-boundary limits,
/// deliberately not configurable: a watch page runs ~1.5 MB and the longest real
/// transcript is a few MB, both orders of magnitude below these values. Without a
/// cap, `text()` will happily read an unbounded response into memory.
const MAX_PAGE_BYTES: u64 = 32 * 1024 * 1024;
const MAX_TRANSCRIPT_BYTES: u64 = 32 * 1024 * 1024;

#[derive(Debug, Clone)]
pub struct Metadata {
    pub title: String,
    pub channel: String,
    pub upload_date: String,
    pub url: String,
}

#[derive(Debug, Clone)]
pub struct Snippet {
    pub text: String,
    /// Start offset in seconds.
    pub start: f64,
}

#[derive(Debug, Clone)]
pub struct Transcript {
    /// Human-readable label, e.g. `English (en) [auto-generated]`.
    pub language: String,
    pub snippets: Vec<Snippet>,
}

pub struct Client {
    http: reqwest::blocking::Client,
    /// Same settings, but bound to an IPv4 local address so it can never use IPv6.
    http_v4: reqwest::blocking::Client,
    /// Set once the default route gets rate-limited, so the rest of the batch goes
    /// straight to IPv4 instead of hitting the captcha page again for every video.
    force_v4: AtomicBool,
}

impl Client {
    pub fn new() -> Result<Self> {
        Ok(Self {
            http: build_http(None)?,
            http_v4: build_http(Some(IpAddr::V4(Ipv4Addr::UNSPECIFIED)))?,
            force_v4: AtomicBool::new(false),
        })
    }

    /// Fetch metadata and the best-matching transcript for one video.
    ///
    /// `languages` is a preference list of language codes; the first track whose
    /// code matches (exactly, or by prefix so `es` matches `es-419`) wins. If none
    /// match, the first available track is used — same fallback as the Python version.
    pub fn fetch(&self, video_id: &str, languages: &[String]) -> Result<(Metadata, Transcript)> {
        let (http, html) = self.watch_page(video_id)?;
        let api_key = scrape(&html, "INNERTUBE_API_KEY")
            .context("INNERTUBE_API_KEY not found in watch page — YouTube changed its layout")?;
        let upload_date = scrape(&html, "uploadDate").map(utc_date).unwrap_or_default();

        let player = player(http, video_id, api_key)?;
        let details = &player["videoDetails"];
        let metadata = Metadata {
            title: details["title"].as_str().unwrap_or("Unknown Title").to_string(),
            channel: details["author"].as_str().unwrap_or("Unknown Channel").to_string(),
            upload_date,
            url: format!("https://www.youtube.com/watch?v={video_id}"),
        };

        let transcript = transcript(http, &player, languages)?;
        Ok((metadata, transcript))
    }

    /// GET the watch page, falling back to IPv4 if Google rate-limits us.
    ///
    /// Google flags whole IPv6 ranges as bot traffic far more readily than IPv4,
    /// answering with a captcha page instead of the video. The connection that got
    /// through is returned so the follow-up API calls use the same route.
    fn watch_page(&self, video_id: &str) -> Result<(&reqwest::blocking::Client, String)> {
        let url = format!("https://www.youtube.com/watch?v={video_id}");
        if !self.force_v4.load(Ordering::Relaxed) {
            let response = self.http.get(&url).header("Accept-Language", "en-US,en").send()?;
            if !is_rate_limited(response.status().as_u16(), response.url().as_str()) {
                return Ok((&self.http, read_capped(response, MAX_PAGE_BYTES, "watch page")?));
            }
            self.force_v4.store(true, Ordering::Relaxed);
        }

        let response = self
            .http_v4
            .get(&url)
            .header("Accept-Language", "en-US,en")
            .send()
            .context("YouTube rate-limited this connection and retrying over IPv4 failed")?;
        if is_rate_limited(response.status().as_u16(), response.url().as_str()) {
            bail!("YouTube is rate-limiting this IP address (it answered with a captcha page) — wait a while and try again");
        }
        Ok((&self.http_v4, read_capped(response, MAX_PAGE_BYTES, "watch page")?))
    }
}

fn build_http(local_address: Option<IpAddr>) -> Result<reqwest::blocking::Client> {
    Ok(reqwest::blocking::Client::builder()
        .user_agent(USER_AGENT)
        .local_address(local_address)
        // Set on the client, not per call site, so no request can hang forever.
        .timeout(std::time::Duration::from_secs(30))
        .connect_timeout(std::time::Duration::from_secs(10))
        .build()?)
}

/// Whether a response is Google's bot check rather than the page we asked for.
///
/// The block shows up as a redirect to `google.com/sorry/...` (which the client
/// follows, ending on a 429), or as a bare 429. Without this check the captcha page
/// gets scraped like a watch page and the error blames YouTube's layout instead.
fn is_rate_limited(status: u16, final_url: &str) -> bool {
    if status == 429 {
        return true;
    }
    reqwest::Url::parse(final_url).is_ok_and(|url| {
        url.host_str().is_some_and(|host| host.ends_with("google.com"))
            && url.path().starts_with("/sorry/")
    })
}

fn player(http: &reqwest::blocking::Client, video_id: &str, api_key: &str) -> Result<Value> {
    let body = json!({
        "videoId": video_id,
        "context": {"client": {
            "clientName": "ANDROID",
            "clientVersion": ANDROID_CLIENT_VERSION,
        }},
    });
    let response = http
        .post(format!("https://www.youtube.com/youtubei/v1/player?key={api_key}"))
        .json(&body)
        .send()?;
    let raw = read_capped(response, MAX_PAGE_BYTES, "player")?;
    let resp: Value =
        serde_json::from_str(&raw).context("player response was not JSON")?;

    let status = resp["playabilityStatus"]["status"].as_str().unwrap_or("UNKNOWN");
    if status != "OK" {
        let reason = resp["playabilityStatus"]["reason"]
            .as_str()
            .unwrap_or("no reason given");
        bail!("video {video_id} is not available: {reason}");
    }
    Ok(resp)
}

fn transcript(
    http: &reqwest::blocking::Client,
    player: &Value,
    languages: &[String],
) -> Result<Transcript> {
    let tracks = player["captions"]["playerCaptionsTracklistRenderer"]["captionTracks"]
        .as_array()
        .filter(|t| !t.is_empty())
        .ok_or_else(|| anyhow!("this video has no transcript"))?;

    let track = pick_track(tracks, languages);
    let base_url = track["baseUrl"].as_str().context("caption track has no baseUrl")?;

    let response = http.get(as_json3(base_url)).send()?;
    let body = read_capped(response, MAX_TRANSCRIPT_BYTES, "transcript")?;
    let parsed: Value = serde_json::from_str(&body)
        .context("YouTube returned no transcript data for this track")?;

    let snippets = parsed["events"]
        .as_array()
        .map(|events| {
            events
                .iter()
                .filter_map(|event| {
                    let text: String = event["segs"]
                        .as_array()?
                        .iter()
                        .filter_map(|seg| seg["utf8"].as_str())
                        .collect();
                    // json3 emits empty padding events; drop them.
                    if text.trim().is_empty() {
                        return None;
                    }
                    Some(Snippet {
                        text: text.trim_end().to_string(),
                        start: event["tStartMs"].as_f64().unwrap_or(0.0) / 1000.0,
                    })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    if snippets.is_empty() {
        bail!("transcript track was empty");
    }

    Ok(Transcript { language: language_label(track), snippets })
}

/// Read a response body as UTF-8, refusing to buffer more than `cap` bytes.
///
/// A declared `Content-Length` is a hint, not permission to allocate, so the cap is
/// enforced on the bytes actually read. Reading one byte past it keeps "exactly at
/// the cap" and "over the cap" distinguishable instead of truncating silently.
fn read_capped(response: reqwest::blocking::Response, cap: u64, what: &str) -> Result<String> {
    let mut buf = Vec::new();
    response.take(cap + 1).read_to_end(&mut buf)?;
    if buf.len() as u64 > cap {
        bail!("{what} response exceeded {cap} bytes");
    }
    Ok(String::from_utf8_lossy(&buf).into_owned())
}

/// Pull the value of a `"key":"value"` pair out of raw HTML.
fn scrape<'a>(html: &'a str, key: &str) -> Option<&'a str> {
    let needle = format!("\"{key}\":\"");
    let start = html.find(&needle)? + needle.len();
    let rest = &html[start..];
    Some(&rest[..rest.find('"')?])
}

/// Convert the page's local-offset ISO timestamp to a UTC `YYYY-MM-DD` date.
///
/// The watch page reports the uploader's local time (e.g. `2005-04-23T20:31:52-07:00`),
/// but yt-dlp reported the UTC date — so the offset has to be applied or the date can
/// land one day early.
fn utc_date(iso: &str) -> String {
    match chrono::DateTime::parse_from_rfc3339(iso) {
        Ok(dt) => dt.to_utc().format("%Y-%m-%d").to_string(),
        // Not a timestamp we recognise — fall back to the leading date portion.
        Err(_) => iso.chars().take(10).collect(),
    }
}

/// Caption baseUrls already carry an `fmt` param and YouTube honours the first one
/// it sees, so it has to be replaced rather than appended.
fn as_json3(base_url: &str) -> String {
    let kept: Vec<&str> = base_url.split('&').filter(|p| !p.starts_with("fmt=")).collect();
    format!("{}&fmt=json3", kept.join("&"))
}

fn pick_track<'a>(tracks: &'a [Value], languages: &[String]) -> &'a Value {
    for wanted in languages {
        let wanted = wanted.to_lowercase();
        for track in tracks {
            let code = track["languageCode"].as_str().unwrap_or("").to_lowercase();
            if code == wanted || code.starts_with(&format!("{wanted}-")) {
                return track;
            }
        }
    }
    &tracks[0]
}

fn language_label(track: &Value) -> String {
    let name = track["name"]["runs"][0]["text"]
        .as_str()
        .or_else(|| track["name"]["simpleText"].as_str())
        .unwrap_or("Unknown");
    let code = track["languageCode"].as_str().unwrap_or("??");
    // The `kind` field is "asr" for machine-generated tracks, absent otherwise.
    if track["kind"].as_str() == Some("asr") {
        format!("{name} ({code}) [auto-generated]")
    } else {
        format!("{name} ({code})")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scrapes_quoted_values() {
        let html = r#"junk {"INNERTUBE_API_KEY":"AIzaSy-abc","uploadDate":"2009-10-24T23:57:33-07:00"}"#;
        assert_eq!(scrape(html, "INNERTUBE_API_KEY"), Some("AIzaSy-abc"));
        assert_eq!(scrape(html, "uploadDate"), Some("2009-10-24T23:57:33-07:00"));
        assert_eq!(scrape(html, "missing"), None);
    }

    #[test]
    fn replaces_existing_fmt_param() {
        let url = "https://yt/api/timedtext?v=abc&fmt=srv3&caps=asr";
        assert_eq!(as_json3(url), "https://yt/api/timedtext?v=abc&caps=asr&fmt=json3");
        // Appends when there is nothing to replace.
        assert_eq!(as_json3("https://yt/x?v=abc"), "https://yt/x?v=abc&fmt=json3");
    }

    #[test]
    fn picks_preferred_language_then_falls_back() {
        let tracks = vec![
            json!({"languageCode": "en", "kind": "asr", "name": {"simpleText": "English"}}),
            json!({"languageCode": "es-419", "name": {"simpleText": "Spanish"}}),
        ];
        // Exact match.
        assert_eq!(pick_track(&tracks, &["en".into()])["languageCode"], "en");
        // Prefix match: `es` should find `es-419`.
        assert_eq!(pick_track(&tracks, &["es".into()])["languageCode"], "es-419");
        // Preference order is honoured.
        assert_eq!(pick_track(&tracks, &["es".into(), "en".into()])["languageCode"], "es-419");
        // No match falls back to the first track.
        assert_eq!(pick_track(&tracks, &["ja".into()])["languageCode"], "en");
    }

    #[test]
    fn converts_upload_dates_to_utc() {
        // 20:31 on the 23rd at -07:00 is already the 24th in UTC.
        assert_eq!(utc_date("2005-04-23T20:31:52-07:00"), "2005-04-24");
        assert_eq!(utc_date("2009-10-24T23:57:33-07:00"), "2009-10-25");
        // Already UTC, and a positive offset that moves the date back.
        assert_eq!(utc_date("2020-06-15T12:00:00+00:00"), "2020-06-15");
        assert_eq!(utc_date("2020-06-15T01:00:00+09:00"), "2020-06-14");
        // Unparseable input degrades to the leading date.
        assert_eq!(utc_date("2020-06-15"), "2020-06-15");
        assert_eq!(utc_date(""), "");
    }

    #[test]
    fn detects_google_rate_limit_responses() {
        // A followed redirect to the captcha page, whatever the final status.
        let sorry = "https://www.google.com/sorry/index?continue=https://www.youtube.com/watch";
        assert!(is_rate_limited(429, sorry));
        assert!(is_rate_limited(200, sorry));
        // A bare 429 without the redirect.
        assert!(is_rate_limited(429, "https://www.youtube.com/watch?v=abc"));
        // A normal watch page, including one whose query merely mentions `sorry`.
        assert!(!is_rate_limited(200, "https://www.youtube.com/watch?v=abc"));
        assert!(!is_rate_limited(200, "https://www.youtube.com/results?q=/sorry/"));
    }

    #[test]
    fn labels_auto_generated_tracks() {
        let asr = json!({"languageCode": "en", "kind": "asr", "name": {"simpleText": "English"}});
        let manual = json!({"languageCode": "en", "name": {"simpleText": "English"}});
        assert_eq!(language_label(&asr), "English (en) [auto-generated]");
        assert_eq!(language_label(&manual), "English (en)");
    }
}
