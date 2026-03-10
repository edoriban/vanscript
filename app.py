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
from theme import COLORS, LANGUAGE_PRESETS, WHISPER_LANGUAGES
from utils import get_default_downloads_folder
from ui.sections import (
    Footer,
    Header,
    LocalFilesTab,
    OptionsPanel,
    OutputFolderPanel,
    StatusLog,
    YouTubeTab,
)

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("green")


class TranscriptDownloaderApp(customtkinter.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("VanScript")

        # Set window icon
        try:
            import platform
            from tkinter import PhotoImage

            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            icon_ico = os.path.join(base_dir, "assets", "icon.ico")
            icon_png = os.path.join(base_dir, "assets", "icon.png")

            if platform.system() == "Windows":
                self.iconbitmap(icon_ico)
            else:
                self.iconphoto(False, PhotoImage(file=icon_png))
        except Exception as e:
            print(f"Failed to load icon: {e}")

        self.geometry("760x780")
        self.minsize(640, 640)
        self.configure(fg_color=COLORS["bg"])

        self._is_downloading = False
        self._selected_files: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)  # tabview
        self.grid_rowconfigure(5, weight=2)  # status log

        # Header
        Header(self).grid(row=0, column=0, padx=20, pady=(16, 0), sticky="ew")

        # Tabview
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

        self.youtube_tab = YouTubeTab(
            self.tabview.tab("YouTube URLs"), download_command=self._start_download
        )
        self.local_files_tab = LocalFilesTab(
            self.tabview.tab("Local Files"),
            select_files_command=self._select_local_files,
            transcribe_command=self._start_transcription,
        )

        # Options
        self.options_panel = OptionsPanel(self)
        self.options_panel.grid(row=2, column=0, padx=20, pady=6, sticky="ew")

        # Output folder
        self.folder_var = customtkinter.StringVar(value=str(get_default_downloads_folder()))
        self.output_panel = OutputFolderPanel(
            self, folder_var=self.folder_var, browse_command=self._browse_folder
        )
        self.output_panel.grid(row=3, column=0, padx=20, pady=(0, 6), sticky="ew")

        # Status log (progress bar + log textbox)
        self.status_log = StatusLog(self)
        self.status_log.grid(row=4, column=0, rowspan=2, padx=20, pady=(0, 6), sticky="nsew")

        # Footer
        Footer(self).grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")

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
        tb = self.local_files_tab.files_textbox
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        if self._selected_files:
            for i, fp in enumerate(self._selected_files, 1):
                name = Path(fp).name
                tb.insert("end", f"  {i}. {name}\n")
        else:
            tb.insert("end", "  No files selected.\n")
        tb.configure(state="disabled")

    def _log(self, message: str) -> None:
        def _append():
            self.status_log.log_textbox.configure(state="normal")
            self.status_log.log_textbox.insert("end", message + "\n")
            self.status_log.log_textbox.see("end")
            self.status_log.log_textbox.configure(state="disabled")

        self.after(0, _append)

    def _set_progress(self, fraction: float) -> None:
        self.after(0, lambda: self.status_log.progress_bar.set(min(fraction, 1.0)))

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.after(0, lambda: self.youtube_tab.download_btn.configure(state=state))
        self.after(0, lambda: self.youtube_tab.lang_dropdown.configure(state=state))
        self.after(0, lambda: self.local_files_tab.transcribe_btn.configure(state=state))
        self.after(0, lambda: self.local_files_tab.select_files_btn.configure(state=state))
        self.after(0, lambda: self.local_files_tab.whisper_model_dropdown.configure(state=state))
        self.after(0, lambda: self.local_files_tab.whisper_lang_dropdown.configure(state=state))
        self.after(0, lambda: self.output_panel.browse_btn.configure(state=state))
        self.after(0, lambda: self.options_panel.timestamps_check.configure(state=state))

    def _clear_log(self) -> None:
        self.status_log.log_textbox.configure(state="normal")
        self.status_log.log_textbox.delete("1.0", "end")
        self.status_log.log_textbox.configure(state="disabled")

    def _open_file(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            pass

    def _start_download(self) -> None:
        if self._is_downloading:
            return

        raw_text = self.youtube_tab.url_textbox.get("1.0", "end").strip()
        if not raw_text:
            self._log("Please paste at least one YouTube URL.")
            return

        self._is_downloading = True
        self._set_controls_enabled(False)
        self.status_log.progress_bar.set(0)
        self._clear_log()

        lang_key = self.youtube_tab.lang_var.get()
        languages = LANGUAGE_PRESETS.get(lang_key, ["es", "en"])

        config = AppConfig(
            output_folder=self.folder_var.get(),
            languages=languages,
            include_timestamps=self.options_panel.timestamps_var.get(),
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

        threading.Thread(target=worker, daemon=True).start()

    def _start_transcription(self) -> None:
        if self._is_downloading:
            return

        if not self._selected_files:
            self._log("Please select at least one media file.")
            return

        self._is_downloading = True
        self._set_controls_enabled(False)
        self.status_log.progress_bar.set(0)
        self._clear_log()

        model_size = WhisperModelSize(self.local_files_tab.whisper_model_var.get())
        lang_key = self.local_files_tab.whisper_lang_var.get()
        language = WHISPER_LANGUAGES.get(lang_key)

        config = AppConfig(
            output_folder=self.folder_var.get(),
            include_timestamps=self.options_panel.timestamps_var.get(),
        )

        file_paths = list(self._selected_files)

        def on_progress(message: str, fraction: float) -> None:
            self._log(message)
            self._set_progress(fraction)

        def worker():
            try:
                output_path = process_local_files(
                    file_paths, config, model_size, language, on_progress
                )
                self._log(f"\nDone! File saved to:\n{output_path}")
                self._open_file(output_path)
            except Exception as exc:
                self._log(f"\nError: {exc}")
            finally:
                self._is_downloading = False
                self._set_controls_enabled(True)

        threading.Thread(target=worker, daemon=True).start()
