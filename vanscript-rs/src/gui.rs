//! egui port of the customtkinter interface: same dark palette, same layout.
//!
//! Fetching happens on a worker thread and reports back over a channel, so the
//! window keeps repainting while transcripts download.

use std::path::PathBuf;
use std::sync::mpsc::{Receiver, Sender, channel};

use eframe::egui::{
    self, Align, Color32, CornerRadius, FontId, Frame, Layout, Margin, RichText, Stroke, TextEdit,
    Vec2,
};

use crate::output::{self, VideoResult};
use crate::youtube;

// --- Colour palette (dark dev-tool + green accent), lifted from the Python app ---
const BG: Color32 = Color32::from_rgb(0x0F, 0x17, 0x2A);
const SURFACE: Color32 = Color32::from_rgb(0x1E, 0x29, 0x3B);
const SURFACE_HI: Color32 = Color32::from_rgb(0x33, 0x41, 0x55);
const BORDER: Color32 = Color32::from_rgb(0x47, 0x55, 0x69);
const TEXT: Color32 = Color32::from_rgb(0xF8, 0xFA, 0xFC);
const TEXT_DIM: Color32 = Color32::from_rgb(0x94, 0xA3, 0xB8);
const ACCENT: Color32 = Color32::from_rgb(0x22, 0xC5, 0x5E);
const ACCENT_HOVER: Color32 = Color32::from_rgb(0x16, 0xA3, 0x4A);

/// Language presets: label -> codes, in the order the dropdown shows them.
const LANGUAGE_PRESETS: &[(&str, &[&str])] = &[
    ("Spanish + English", &["es", "en"]),
    ("English + Spanish", &["en", "es"]),
    ("English only", &["en"]),
    ("Spanish only", &["es"]),
    ("Portuguese + English", &["pt", "en"]),
    ("French + English", &["fr", "en"]),
    ("German + English", &["de", "en"]),
];

/// What the worker thread reports back to the UI.
enum Update {
    Log(String),
    Progress(f32),
    Finished(Result<PathBuf, String>),
}

pub struct App {
    urls: String,
    language: usize,
    include_timestamps: bool,
    folder: String,
    log: String,
    progress: f32,
    /// `Some` while a download is running; the UI disables its controls then.
    updates: Option<Receiver<Update>>,
}

impl App {
    pub fn new(folder: PathBuf) -> Self {
        Self {
            urls: String::new(),
            language: 0,
            include_timestamps: false,
            folder: folder.to_string_lossy().into_owned(),
            log: String::new(),
            progress: 0.0,
            updates: None,
        }
    }

    fn busy(&self) -> bool {
        self.updates.is_some()
    }

    fn start(&mut self) {
        let (ids, invalid) = output::parse_url_list(&self.urls);
        self.log.clear();
        for line in &invalid {
            self.log.push_str(&format!("Skipped (not a YouTube URL): {line}\n"));
        }
        if ids.is_empty() {
            self.log.push_str("Please paste at least one YouTube URL.\n");
            return;
        }

        let (tx, rx) = channel();
        self.updates = Some(rx);
        self.progress = 0.0;

        let languages: Vec<String> =
            LANGUAGE_PRESETS[self.language].1.iter().map(|s| s.to_string()).collect();
        let folder = PathBuf::from(self.folder.clone());
        let timestamps = self.include_timestamps;

        std::thread::spawn(move || {
            let result = download(&tx, ids, &languages, folder, timestamps);
            let _ = tx.send(Update::Finished(result.map_err(|e| e.to_string())));
        });
    }

    /// Drain whatever the worker has sent since the last frame.
    fn poll_worker(&mut self) {
        let Some(rx) = &self.updates else { return };
        let mut finished = false;
        while let Ok(update) = rx.try_recv() {
            match update {
                Update::Log(line) => self.log.push_str(&format!("{line}\n")),
                Update::Progress(fraction) => self.progress = fraction,
                Update::Finished(Ok(path)) => {
                    self.log.push_str(&format!("Saved to: {}\n", path.display()));
                    self.progress = 1.0;
                    open_in_default_app(&path);
                    finished = true;
                }
                Update::Finished(Err(error)) => {
                    self.log.push_str(&format!("Error: {error}\n"));
                    finished = true;
                }
            }
        }
        if finished {
            self.updates = None;
        }
    }
}

/// Fetch every video and write the output file, reporting progress as it goes.
/// A single video failing never aborts the rest.
fn download(
    tx: &Sender<Update>,
    ids: Vec<String>,
    languages: &[String],
    folder: PathBuf,
    include_timestamps: bool,
) -> anyhow::Result<PathBuf> {
    let client = youtube::Client::new()?;
    let total = ids.len();
    let _ = tx.send(Update::Log(format!("Found {total} video(s). Starting...")));

    let mut results = Vec::with_capacity(total);
    for (i, id) in ids.iter().enumerate() {
        let _ = tx.send(Update::Progress(i as f32 / total as f32 * 0.9 + 0.05));
        let _ = tx.send(Update::Log(format!("[{}/{total}] Fetching {id}...", i + 1)));

        let data = client.fetch(id, languages).map_err(|e| e.to_string());
        let line = match &data {
            Ok((meta, transcript)) => format!(
                "[{}/{total}] Done: {} ({} lines, {})",
                i + 1,
                meta.title,
                transcript.snippets.len(),
                transcript.language,
            ),
            Err(error) => format!("[{}/{total}] Failed: {error}", i + 1),
        };
        let _ = tx.send(Update::Log(line));
        results.push(VideoResult { video_id: id.clone(), data });
    }

    let _ = tx.send(Update::Log("Building output file...".into()));
    let _ = tx.send(Update::Progress(0.95));

    std::fs::create_dir_all(&folder)?;
    let path = output::ensure_unique_path(folder.join(output::build_output_filename(&results)));
    std::fs::write(&path, output::render(&results, include_timestamps))?;
    Ok(path)
}

fn open_in_default_app(path: &std::path::Path) {
    let opener = if cfg!(target_os = "macos") { "open" } else { "xdg-open" };
    let _ = std::process::Command::new(opener).arg(path).spawn();
}

/// A rounded panel on the surface colour — the CTkFrame equivalent.
fn panel(radius: u8) -> Frame {
    Frame::new()
        .fill(SURFACE)
        .corner_radius(CornerRadius::same(radius))
        .inner_margin(Margin::same(12))
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_worker();
        // Repaint while working so log lines and the progress bar keep flowing.
        if self.busy() {
            ctx.request_repaint_after(std::time::Duration::from_millis(100));
        }

        apply_theme(ctx);

        egui::TopBottomPanel::bottom("footer")
            .show_separator_line(false)
            .frame(Frame::new().fill(BG).inner_margin(Margin::symmetric(16, 8)))
            .show(ctx, |ui| self.footer(ui));

        egui::CentralPanel::default()
            .frame(Frame::new().fill(BG).inner_margin(Margin::same(16)))
            .show(ctx, |ui| {
                self.header(ui);
                ui.add_space(10.0);
                self.controls(ui);
                ui.add_space(6.0);
                self.url_input(ui);
                ui.add_space(6.0);
                self.options(ui);
                ui.add_space(6.0);
                self.output_folder(ui);
                ui.add_space(8.0);
                ui.add(
                    egui::ProgressBar::new(self.progress)
                        .desired_height(14.0)
                        .corner_radius(CornerRadius::same(6))
                        .fill(ACCENT),
                );
                ui.add_space(8.0);
                self.status_log(ui);
            });
    }
}

impl App {
    fn header(&self, ui: &mut egui::Ui) {
        panel(12).show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.label(
                    RichText::new("VS")
                        .font(FontId::monospace(24.0))
                        .strong()
                        .color(ACCENT),
                );
                ui.add_space(8.0);
                ui.label(RichText::new("VanScript").size(22.0).strong().color(TEXT));
                ui.add_space(12.0);
                ui.label(RichText::new("Transcript Downloader").size(12.0).color(TEXT_DIM));
            });
            ui.add_space(6.0);
            // Thin accent bar under the title.
            let width = ui.available_width();
            let (rect, _) = ui.allocate_exact_size(Vec2::new(width, 2.0), egui::Sense::hover());
            ui.painter().rect_filled(rect, 0.0, ACCENT);
        });
    }

    fn controls(&mut self, ui: &mut egui::Ui) {
        let enabled = !self.busy();
        ui.horizontal(|ui| {
            ui.label(RichText::new("Language:").size(12.0).color(TEXT_DIM));
            ui.add_enabled_ui(enabled, |ui| {
                egui::ComboBox::from_id_salt("language")
                    .width(200.0)
                    .selected_text(LANGUAGE_PRESETS[self.language].0)
                    .show_ui(ui, |ui| {
                        for (i, (label, _)) in LANGUAGE_PRESETS.iter().enumerate() {
                            ui.selectable_value(&mut self.language, i, *label);
                        }
                    });
            });

            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                let label = if enabled { "Download Transcripts" } else { "Downloading..." };
                let button = egui::Button::new(
                    RichText::new(label).size(13.0).strong().color(BG),
                )
                .fill(ACCENT)
                .corner_radius(CornerRadius::same(10))
                .min_size(Vec2::new(0.0, 36.0));
                if ui.add_enabled(enabled, button).clicked() {
                    self.start();
                }
            });
        });
    }

    fn url_input(&mut self, ui: &mut egui::Ui) {
        ui.label(
            RichText::new("PASTE YOUTUBE URLS")
                .font(FontId::monospace(11.0))
                .strong()
                .color(TEXT_DIM),
        );
        ui.add_space(2.0);
        ui.add_enabled_ui(!self.busy(), |ui| {
            ui.add(
                TextEdit::multiline(&mut self.urls)
                    .desired_width(f32::INFINITY)
                    .desired_rows(7)
                    .hint_text("https://www.youtube.com/watch?v=..."),
            );
        });
    }

    fn options(&mut self, ui: &mut egui::Ui) {
        panel(10).show(ui, |ui| {
            ui.add_enabled_ui(!self.busy(), |ui| {
                ui.checkbox(
                    &mut self.include_timestamps,
                    RichText::new("Include timestamps [HH:MM:SS]").size(12.0).color(TEXT),
                );
            });
        });
    }

    fn output_folder(&mut self, ui: &mut egui::Ui) {
        let enabled = !self.busy();
        panel(10).show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.label(RichText::new("Save to:").size(12.0).color(TEXT_DIM));
                // Right-to-left so Browse pins to the edge and the path field takes the rest.
                ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                    let browse = ui.add_enabled(
                        enabled,
                        egui::Button::new(RichText::new("Browse").size(12.0).color(TEXT))
                            .fill(SURFACE_HI)
                            .corner_radius(CornerRadius::same(8))
                            .min_size(Vec2::new(80.0, 0.0)),
                    );
                    if browse.clicked() {
                        if let Some(dir) =
                            rfd::FileDialog::new().set_directory(&self.folder).pick_folder()
                        {
                            self.folder = dir.to_string_lossy().into_owned();
                        }
                    }
                    ui.add_enabled_ui(enabled, |ui| {
                        ui.add(
                            TextEdit::singleline(&mut self.folder)
                                .font(FontId::monospace(12.0))
                                .desired_width(f32::INFINITY),
                        );
                    });
                });
            });
        });
    }

    fn status_log(&mut self, ui: &mut egui::Ui) {
        ui.label(
            RichText::new("STATUS")
                .font(FontId::monospace(11.0))
                .strong()
                .color(TEXT_DIM),
        );
        ui.add_space(2.0);
        Frame::new()
            .fill(SURFACE)
            .stroke(Stroke::new(1.0_f32, BORDER))
            .corner_radius(CornerRadius::same(10))
            .inner_margin(Margin::same(10))
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .auto_shrink([false, false])
                    .stick_to_bottom(true)
                    .min_scrolled_height(120.0)
                    .show(ui, |ui| {
                        ui.add(
                            egui::Label::new(
                                RichText::new(&self.log)
                                    .font(FontId::monospace(12.0))
                                    .color(TEXT_DIM),
                            )
                            .wrap(),
                        );
                    });
            });
    }

    fn footer(&self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.label(RichText::new(concat!("VanScript v", env!("CARGO_PKG_VERSION"))).font(FontId::monospace(10.0)).color(BORDER));
            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                ui.label(RichText::new("by VanDev").size(10.0).strong().color(TEXT_DIM));
            });
        });
    }
}

fn apply_theme(ctx: &egui::Context) {
    let mut style = (*ctx.style()).clone();
    let w = &mut style.visuals.widgets;

    style.visuals.dark_mode = true;
    style.visuals.override_text_color = Some(TEXT);
    style.visuals.panel_fill = BG;
    style.visuals.window_fill = BG;
    style.visuals.extreme_bg_color = SURFACE_HI; // text edit backgrounds
    style.visuals.selection.bg_fill = ACCENT.gamma_multiply(0.4);

    // Inputs and idle widgets sit on the elevated surface; hover reaches for the accent.
    w.noninteractive.bg_fill = SURFACE;
    w.noninteractive.fg_stroke = Stroke::new(1.0_f32, TEXT_DIM);
    w.inactive.bg_fill = SURFACE_HI;
    w.inactive.weak_bg_fill = SURFACE_HI;
    w.inactive.fg_stroke = Stroke::new(1.0_f32, TEXT);
    w.hovered.bg_fill = BORDER;
    w.hovered.weak_bg_fill = BORDER;
    w.hovered.bg_stroke = Stroke::new(1.0_f32, ACCENT);
    w.active.bg_fill = ACCENT_HOVER;
    w.active.weak_bg_fill = ACCENT_HOVER;
    for widget in [&mut w.inactive, &mut w.hovered, &mut w.active, &mut w.noninteractive] {
        widget.corner_radius = CornerRadius::same(4);
    }
    ctx.set_style(style);
}

pub fn run(folder: PathBuf) -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([760.0, 780.0])
            .with_min_inner_size([640.0, 640.0])
            .with_title("VanScript"),
        ..Default::default()
    };
    eframe::run_native("VanScript", options, Box::new(|_cc| Ok(Box::new(App::new(folder)))))
}
