"""CustomTkinter GUI for VanScript — YouTube transcript downloader by VanDev."""

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter

from core import process_all_videos, process_local_files
from models import AppConfig, WhisperModelSize
from utils import get_default_downloads_folder

# Language presets: label -> language codes (for YouTube tab)
LANGUAGE_PRESETS = {
    "Spanish + English": ["es", "en"],
    "English + Spanish": ["en", "es"],
    "English only": ["en"],
    "Spanish only": ["es"],
    "Portuguese + English": ["pt", "en"],
    "French + English": ["fr", "en"],
    "German + English": ["de", "en"],
}

# Whisper language codes: label -> code (for Local Files tab)
WHISPER_LANGUAGES = {
    "Spanish (es)": "es",
    "English (en)": "en",
    "Portuguese (pt)": "pt",
    "French (fr)": "fr",
    "German (de)": "de",
    "Italian (it)": "it",
    "Japanese (ja)": "ja",
    "Chinese (zh)": "zh",
    "Korean (ko)": "ko",
    "Auto-detect": None,
}

# --- Color palette (dark dev-tool + green accent) ---
COLORS = {
    "bg":         "#0F172A",  # deep navy background
    "surface":    "#1E293B",  # card/panel surface
    "surface_hi": "#334155",  # elevated surface (inputs, hover)
    "border":     "#475569",  # subtle borders
    "text":       "#F8FAFC",  # primary text
    "text_dim":   "#94A3B8",  # secondary/muted text
    "accent":     "#22C55E",  # green CTA
    "accent_hover": "#16A34A",  # green hover
}

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("green")


class TranscriptDownloaderApp(customtkinter.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("VanScript")
        self.geometry("760x780")
        self.minsize(640, 640)
        self.configure(fg_color=COLORS["bg"])

        self._is_downloading = False
        self._selected_files: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        # Row weights: tabview (row 1) and log area (row 7) expand
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(7, weight=2)

        # =====================================================================
        # HEADER
        # =====================================================================
        header_frame = customtkinter.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=12)
        header_frame.grid(row=0, column=0, padx=20, pady=(16, 0), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_row = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(14, 2))

        customtkinter.CTkLabel(
            title_row, text="VS",
            font=("Consolas", 24, "bold"), text_color=COLORS["accent"],
        ).pack(side="left")

        customtkinter.CTkLabel(
            title_row, text="VanScript",
            font=("Segoe UI", 22, "bold"), text_color=COLORS["text"],
        ).pack(side="left", padx=(8, 0))

        customtkinter.CTkLabel(
            title_row, text="Transcript Downloader",
            font=("Segoe UI", 12), text_color=COLORS["text_dim"],
        ).pack(side="left", padx=(12, 0), pady=(5, 0))

        # Thin accent bar under header
        accent_bar = customtkinter.CTkFrame(
            header_frame, fg_color=COLORS["accent"], height=2, corner_radius=0
        )
        accent_bar.pack(fill="x", padx=16, pady=(6, 12))

        # =====================================================================
        # TABVIEW (YouTube URLs | Local Files)
        # =====================================================================
        self.tabview = customtkinter.CTkTabview(
            self,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface_hi"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["surface_hi"],
            segmented_button_unselected_hover_color=COLORS["border"],
            corner_radius=12,
        )
        self.tabview.grid(row=1, column=0, padx=20, pady=(10, 4), sticky="nsew")

        self.tabview.add("YouTube URLs")
        self.tabview.add("Local Files")

        self._build_youtube_tab()
        self._build_local_files_tab()

        # =====================================================================
        # SHARED OPTIONS PANEL
        # =====================================================================
        opts_panel = customtkinter.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        opts_panel.grid(row=2, column=0, padx=20, pady=6, sticky="ew")
        opts_panel.grid_columnconfigure(1, weight=1)

        # Timestamps
        self.timestamps_var = customtkinter.BooleanVar(value=False)
        self.timestamps_check = customtkinter.CTkCheckBox(
            opts_panel, text="Include timestamps [HH:MM:SS]",
            variable=self.timestamps_var,
            fg_color=COLORS["surface_hi"], hover_color=COLORS["accent"],
            checkmark_color=COLORS["bg"],
            font=("Segoe UI", 12), text_color=COLORS["text"],
        )
        self.timestamps_check.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        # =====================================================================
        # OUTPUT FOLDER
        # =====================================================================
        folder_panel = customtkinter.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        folder_panel.grid(row=3, column=0, padx=20, pady=(0, 6), sticky="ew")
        folder_panel.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(
            folder_panel, text="Save to:",
            font=("Segoe UI", 12), text_color=COLORS["text_dim"],
        ).grid(row=0, column=0, padx=(14, 6), pady=10, sticky="w")

        self.folder_var = customtkinter.StringVar(value=str(get_default_downloads_folder()))
        self.folder_entry = customtkinter.CTkEntry(
            folder_panel, textvariable=self.folder_var,
            fg_color=COLORS["surface_hi"], border_color=COLORS["border"],
            text_color=COLORS["text"], font=("Consolas", 12),
        )
        self.folder_entry.grid(row=0, column=1, padx=(0, 6), pady=10, sticky="ew")

        self.browse_btn = customtkinter.CTkButton(
            folder_panel, text="Browse", width=80, corner_radius=8,
            fg_color=COLORS["surface_hi"], hover_color=COLORS["border"],
            text_color=COLORS["text"], font=("Segoe UI", 12),
            command=self._browse_folder,
        )
        self.browse_btn.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="e")

        # =====================================================================
        # PROGRESS BAR
        # =====================================================================
        progress_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=4, column=0, padx=20, pady=(4, 6), sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = customtkinter.CTkProgressBar(
            progress_frame, corner_radius=6, height=14,
            fg_color=COLORS["surface"], progress_color=COLORS["accent"],
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=4)
        self.progress_bar.set(0)

        # =====================================================================
        # STATUS LOG
        # =====================================================================
        customtkinter.CTkLabel(
            self, text="STATUS",
            font=("Consolas", 11, "bold"), text_color=COLORS["text_dim"],
        ).grid(row=6, column=0, padx=24, pady=(8, 4), sticky="w")

        self.log_textbox = customtkinter.CTkTextbox(
            self, state="disabled", wrap="word", corner_radius=10,
            fg_color=COLORS["surface"], text_color=COLORS["text_dim"],
            border_width=1, border_color=COLORS["border"],
            font=("Consolas", 12),
        )
        self.log_textbox.grid(row=7, column=0, padx=20, pady=(0, 6), sticky="nsew")

        # =====================================================================
        # FOOTER
        # =====================================================================
        footer_frame = customtkinter.CTkFrame(self, fg_color="transparent", height=28)
        footer_frame.grid(row=8, column=0, padx=20, pady=(0, 10), sticky="ew")
        footer_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            footer_frame, text="VanScript v1.1",
            font=("Consolas", 10), text_color=COLORS["border"],
        ).pack(side="left")

        customtkinter.CTkLabel(
            footer_frame, text="by VanDev",
            font=("Segoe UI", 10, "bold"), text_color=COLORS["text_dim"],
        ).pack(side="right")

    # ----- Tab builders -----

    def _build_youtube_tab(self) -> None:
        tab = self.tabview.tab("YouTube URLs")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Controls row
        controls_frame = customtkinter.CTkFrame(tab, fg_color="transparent")
        controls_frame.grid(row=0, column=0, padx=4, pady=(4, 4), sticky="ew")

        customtkinter.CTkLabel(
            controls_frame, text="Language:",
            font=("Segoe UI", 12), text_color=COLORS["text_dim"],
        ).pack(side="left", padx=(4, 4))

        self.lang_var = customtkinter.StringVar(value="Spanish + English")
        self.lang_dropdown = customtkinter.CTkOptionMenu(
            controls_frame, variable=self.lang_var,
            values=list(LANGUAGE_PRESETS.keys()), width=200,
            fg_color=COLORS["surface_hi"], button_color=COLORS["border"],
            button_hover_color=COLORS["accent"], dropdown_fg_color=COLORS["surface"],
            font=("Segoe UI", 12),
        )
        self.lang_dropdown.pack(side="left", padx=(0, 8))

        self.download_btn = customtkinter.CTkButton(
            controls_frame, text="Download Transcripts",
            font=("Segoe UI", 13, "bold"), height=36, corner_radius=10,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["bg"],
            command=self._start_download,
        )
        self.download_btn.pack(side="right", padx=(8, 4))

        # URL label
        customtkinter.CTkLabel(
            tab, text="PASTE YOUTUBE URLS",
            font=("Consolas", 11, "bold"), text_color=COLORS["text_dim"],
        ).grid(row=1, column=0, padx=8, pady=(4, 2), sticky="w")

        # URL textbox
        self.url_textbox = customtkinter.CTkTextbox(
            tab, wrap="word", corner_radius=10,
            fg_color=COLORS["surface_hi"], text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            font=("Consolas", 13),
        )
        self.url_textbox.grid(row=2, column=0, padx=4, pady=(0, 4), sticky="nsew")

    def _build_local_files_tab(self) -> None:
        tab = self.tabview.tab("Local Files")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Controls row
        controls_frame = customtkinter.CTkFrame(tab, fg_color="transparent")
        controls_frame.grid(row=0, column=0, padx=4, pady=(4, 4), sticky="ew")

        # Select Files button
        self.select_files_btn = customtkinter.CTkButton(
            controls_frame, text="Select Files", width=120, corner_radius=8,
            fg_color=COLORS["surface_hi"], hover_color=COLORS["border"],
            text_color=COLORS["text"], font=("Segoe UI", 12),
            command=self._select_local_files,
        )
        self.select_files_btn.pack(side="left", padx=(4, 8))

        # Whisper model dropdown
        customtkinter.CTkLabel(
            controls_frame, text="Model:",
            font=("Segoe UI", 12), text_color=COLORS["text_dim"],
        ).pack(side="left", padx=(8, 4))

        self.whisper_model_var = customtkinter.StringVar(value="base")
        self.whisper_model_dropdown = customtkinter.CTkOptionMenu(
            controls_frame, variable=self.whisper_model_var,
            values=[s.value for s in WhisperModelSize], width=100,
            fg_color=COLORS["surface_hi"], button_color=COLORS["border"],
            button_hover_color=COLORS["accent"], dropdown_fg_color=COLORS["surface"],
            font=("Segoe UI", 12),
        )
        self.whisper_model_dropdown.pack(side="left", padx=(0, 8))

        # Language dropdown
        customtkinter.CTkLabel(
            controls_frame, text="Language:",
            font=("Segoe UI", 12), text_color=COLORS["text_dim"],
        ).pack(side="left", padx=(8, 4))

        self.whisper_lang_var = customtkinter.StringVar(value="Spanish (es)")
        self.whisper_lang_dropdown = customtkinter.CTkOptionMenu(
            controls_frame, variable=self.whisper_lang_var,
            values=list(WHISPER_LANGUAGES.keys()), width=160,
            fg_color=COLORS["surface_hi"], button_color=COLORS["border"],
            button_hover_color=COLORS["accent"], dropdown_fg_color=COLORS["surface"],
            font=("Segoe UI", 12),
        )
        self.whisper_lang_dropdown.pack(side="left", padx=(0, 8))

        # Transcribe button
        self.transcribe_btn = customtkinter.CTkButton(
            controls_frame, text="Transcribe",
            font=("Segoe UI", 13, "bold"), height=36, corner_radius=10,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["bg"],
            command=self._start_transcription,
        )
        self.transcribe_btn.pack(side="right", padx=(8, 4))

        # Files label
        customtkinter.CTkLabel(
            tab, text="SELECTED FILES",
            font=("Consolas", 11, "bold"), text_color=COLORS["text_dim"],
        ).grid(row=1, column=0, padx=8, pady=(4, 2), sticky="w")

        # Files list display
        self.files_textbox = customtkinter.CTkTextbox(
            tab, state="disabled", wrap="word", corner_radius=10,
            fg_color=COLORS["surface_hi"], text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            font=("Consolas", 12),
        )
        self.files_textbox.grid(row=2, column=0, padx=4, pady=(0, 4), sticky="nsew")

    # ----- Actions -----

    def _browse_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def _select_local_files(self) -> None:
        filetypes = [
            ("Media files", "*.mp4 *.mkv *.mp3 *.wav *.m4a *.webm *.ogg *.flac"),
            ("All files", "*.*"),
        ]
        files = filedialog.askopenfilenames(filetypes=filetypes)
        if files:
            self._selected_files = list(files)
            self._update_files_display()

    def _update_files_display(self) -> None:
        self.files_textbox.configure(state="normal")
        self.files_textbox.delete("1.0", "end")
        if self._selected_files:
            for i, fp in enumerate(self._selected_files, 1):
                name = Path(fp).name
                self.files_textbox.insert("end", f"  {i}. {name}\n")
        else:
            self.files_textbox.insert("end", "  No files selected.\n")
        self.files_textbox.configure(state="disabled")

    def _log(self, message: str) -> None:
        """Append a message to the log textbox (thread-safe via after())."""
        def _append():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", message + "\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _append)

    def _set_progress(self, fraction: float) -> None:
        self.after(0, lambda: self.progress_bar.set(min(fraction, 1.0)))

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.after(0, lambda: self.download_btn.configure(state=state))
        self.after(0, lambda: self.transcribe_btn.configure(state=state))
        self.after(0, lambda: self.browse_btn.configure(state=state))
        self.after(0, lambda: self.select_files_btn.configure(state=state))
        self.after(0, lambda: self.lang_dropdown.configure(state=state))
        self.after(0, lambda: self.whisper_model_dropdown.configure(state=state))
        self.after(0, lambda: self.whisper_lang_dropdown.configure(state=state))
        self.after(0, lambda: self.timestamps_check.configure(state=state))

    def _clear_log(self) -> None:
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def _open_file(self, path: Path) -> None:
        """Open a file with the OS default application."""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                # Linux / WSL
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            pass

    def _start_download(self) -> None:
        """Start YouTube transcript download (YouTube URLs tab)."""
        if self._is_downloading:
            return

        raw_text = self.url_textbox.get("1.0", "end").strip()
        if not raw_text:
            self._log("Please paste at least one YouTube URL.")
            return

        self._is_downloading = True
        self._set_controls_enabled(False)
        self.progress_bar.set(0)
        self._clear_log()

        lang_key = self.lang_var.get()
        languages = LANGUAGE_PRESETS.get(lang_key, ["es", "en"])

        config = AppConfig(
            output_folder=self.folder_var.get(),
            languages=languages,
            include_timestamps=self.timestamps_var.get(),
        )

        def on_progress(message: str, fraction: float) -> None:
            self._log(message)
            self._set_progress(fraction)

        def worker():
            try:
                output_path = process_all_videos(raw_text, config, on_progress)
                self._log(f"\nDone! File saved to:\n{output_path}")
                self._open_file(output_path)
            except Exception as exc:
                self._log(f"\nError: {exc}")
            finally:
                self._is_downloading = False
                self._set_controls_enabled(True)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _start_transcription(self) -> None:
        """Start local file transcription (Local Files tab)."""
        if self._is_downloading:
            return

        if not self._selected_files:
            self._log("Please select at least one media file.")
            return

        self._is_downloading = True
        self._set_controls_enabled(False)
        self.progress_bar.set(0)
        self._clear_log()

        # Get Whisper settings
        model_size_str = self.whisper_model_var.get()
        model_size = WhisperModelSize(model_size_str)

        lang_key = self.whisper_lang_var.get()
        language = WHISPER_LANGUAGES.get(lang_key)

        config = AppConfig(
            output_folder=self.folder_var.get(),
            include_timestamps=self.timestamps_var.get(),
        )

        file_paths = list(self._selected_files)

        def on_progress(message: str, fraction: float) -> None:
            self._log(message)
            self._set_progress(fraction)

        def worker():
            try:
                output_path = process_local_files(
                    file_paths, config, model_size, language, on_progress,
                )
                self._log(f"\nDone! File saved to:\n{output_path}")
                self._open_file(output_path)
            except Exception as exc:
                self._log(f"\nError: {exc}")
            finally:
                self._is_downloading = False
                self._set_controls_enabled(True)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
