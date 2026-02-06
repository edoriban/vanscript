"""CustomTkinter GUI for VanScript — YouTube transcript downloader by VanDev."""

import threading
from tkinter import filedialog

import customtkinter

from core import process_all_videos
from models import AppConfig
from utils import get_default_downloads_folder

# Language presets: label -> language codes
LANGUAGE_PRESETS = {
    "Spanish + English": ["es", "en"],
    "English + Spanish": ["en", "es"],
    "English only": ["en"],
    "Spanish only": ["es"],
    "Portuguese + English": ["pt", "en"],
    "French + English": ["fr", "en"],
    "German + English": ["de", "en"],
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
        self.geometry("760x740")
        self.minsize(640, 600)
        self.configure(fg_color=COLORS["bg"])

        self._is_downloading = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        # Row weights: URL area (row 3) and log area (row 9) expand
        self.grid_rowconfigure(3, weight=3)
        self.grid_rowconfigure(9, weight=2)

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
            title_row, text="YouTube Transcript Downloader",
            font=("Segoe UI", 12), text_color=COLORS["text_dim"],
        ).pack(side="left", padx=(12, 0), pady=(5, 0))

        # Thin accent bar under header
        accent_bar = customtkinter.CTkFrame(
            header_frame, fg_color=COLORS["accent"], height=2, corner_radius=0
        )
        accent_bar.pack(fill="x", padx=16, pady=(6, 12))

        # =====================================================================
        # URL INPUT SECTION
        # =====================================================================
        url_label = customtkinter.CTkLabel(
            self, text="PASTE YOUTUBE URLS",
            font=("Consolas", 11, "bold"), text_color=COLORS["text_dim"],
        )
        url_label.grid(row=2, column=0, padx=24, pady=(14, 4), sticky="w")

        self.url_textbox = customtkinter.CTkTextbox(
            self, wrap="word", corner_radius=10,
            fg_color=COLORS["surface"], text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            font=("Consolas", 13),
        )
        self.url_textbox.grid(row=3, column=0, padx=20, pady=(0, 4), sticky="nsew")

        # =====================================================================
        # OPTIONS PANEL
        # =====================================================================
        opts_panel = customtkinter.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        opts_panel.grid(row=4, column=0, padx=20, pady=6, sticky="ew")
        opts_panel.grid_columnconfigure(1, weight=1)

        # Language
        customtkinter.CTkLabel(
            opts_panel, text="Language:",
            font=("Segoe UI", 12), text_color=COLORS["text_dim"],
        ).grid(row=0, column=0, padx=(14, 6), pady=10, sticky="w")

        self.lang_var = customtkinter.StringVar(value="Spanish + English")
        self.lang_dropdown = customtkinter.CTkOptionMenu(
            opts_panel, variable=self.lang_var,
            values=list(LANGUAGE_PRESETS.keys()), width=200,
            fg_color=COLORS["surface_hi"], button_color=COLORS["border"],
            button_hover_color=COLORS["accent"], dropdown_fg_color=COLORS["surface"],
            font=("Segoe UI", 12),
        )
        self.lang_dropdown.grid(row=0, column=1, padx=(0, 16), pady=10, sticky="w")

        # Timestamps
        self.timestamps_var = customtkinter.BooleanVar(value=False)
        self.timestamps_check = customtkinter.CTkCheckBox(
            opts_panel, text="Include timestamps [HH:MM:SS]",
            variable=self.timestamps_var,
            fg_color=COLORS["surface_hi"], hover_color=COLORS["accent"],
            checkmark_color=COLORS["bg"],
            font=("Segoe UI", 12), text_color=COLORS["text"],
        )
        self.timestamps_check.grid(row=0, column=2, padx=(0, 14), pady=10, sticky="e")

        # =====================================================================
        # OUTPUT FOLDER
        # =====================================================================
        folder_panel = customtkinter.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        folder_panel.grid(row=5, column=0, padx=20, pady=(0, 6), sticky="ew")
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
        # ACTION ROW (download button + progress)
        # =====================================================================
        action_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=6, column=0, padx=20, pady=(4, 6), sticky="ew")
        action_frame.grid_columnconfigure(1, weight=1)

        self.download_btn = customtkinter.CTkButton(
            action_frame, text="Download Transcripts",
            font=("Segoe UI", 14, "bold"), height=42, corner_radius=10,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["bg"],
            command=self._start_download,
        )
        self.download_btn.grid(row=0, column=0, padx=(0, 12), sticky="w")

        self.progress_bar = customtkinter.CTkProgressBar(
            action_frame, corner_radius=6, height=14,
            fg_color=COLORS["surface"], progress_color=COLORS["accent"],
        )
        self.progress_bar.grid(row=0, column=1, sticky="ew", pady=4)
        self.progress_bar.set(0)

        # =====================================================================
        # STATUS LOG
        # =====================================================================
        customtkinter.CTkLabel(
            self, text="STATUS",
            font=("Consolas", 11, "bold"), text_color=COLORS["text_dim"],
        ).grid(row=8, column=0, padx=24, pady=(8, 4), sticky="w")

        self.log_textbox = customtkinter.CTkTextbox(
            self, state="disabled", wrap="word", corner_radius=10,
            fg_color=COLORS["surface"], text_color=COLORS["text_dim"],
            border_width=1, border_color=COLORS["border"],
            font=("Consolas", 12),
        )
        self.log_textbox.grid(row=9, column=0, padx=20, pady=(0, 6), sticky="nsew")

        # =====================================================================
        # FOOTER
        # =====================================================================
        footer_frame = customtkinter.CTkFrame(self, fg_color="transparent", height=28)
        footer_frame.grid(row=10, column=0, padx=20, pady=(0, 10), sticky="ew")
        footer_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            footer_frame, text="VanScript v1.0",
            font=("Consolas", 10), text_color=COLORS["border"],
        ).pack(side="left")

        customtkinter.CTkLabel(
            footer_frame, text="by VanDev",
            font=("Segoe UI", 10, "bold"), text_color=COLORS["text_dim"],
        ).pack(side="right")

    # ----- Actions -----

    def _browse_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

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
        self.after(0, lambda: self.browse_btn.configure(state=state))
        self.after(0, lambda: self.lang_dropdown.configure(state=state))
        self.after(0, lambda: self.timestamps_check.configure(state=state))

    def _start_download(self) -> None:
        if self._is_downloading:
            return

        raw_text = self.url_textbox.get("1.0", "end").strip()
        if not raw_text:
            self._log("Please paste at least one YouTube URL.")
            return

        self._is_downloading = True
        self._set_controls_enabled(False)
        self.progress_bar.set(0)

        # Clear log
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

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
            except Exception as exc:
                self._log(f"\nError: {exc}")
            finally:
                self._is_downloading = False
                self._set_controls_enabled(True)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
