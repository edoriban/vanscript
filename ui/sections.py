"""UI sections — self-contained panels for the VanScript interface."""

import customtkinter

from theme import COLORS, FONTS, LANGUAGE_PRESETS, WHISPER_LANGUAGES
from models import WhisperModelSize
from ui.widgets import (
    AppCheckbox,
    AppProgressBar,
    AppTextbox,
    FolderSelector,
    LabeledDropdown,
    PrimaryButton,
    SecondaryButton,
    SectionLabel,
    SectionTextbox,
)


class Header(customtkinter.CTkFrame):
    """App header with logo, title, and accent bar."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=12, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        title_row = customtkinter.CTkFrame(self, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(14, 2))

        customtkinter.CTkLabel(
            title_row, text="VS", font=FONTS["mono_logo"], text_color=COLORS["accent"]
        ).pack(side="left")

        customtkinter.CTkLabel(
            title_row, text="VanScript", font=FONTS["ui_title"], text_color=COLORS["text"]
        ).pack(side="left", padx=(8, 0))

        customtkinter.CTkLabel(
            title_row,
            text="Transcript Downloader",
            font=FONTS["ui"],
            text_color=COLORS["text_dim"],
        ).pack(side="left", padx=(12, 0), pady=(5, 0))

        accent_bar = customtkinter.CTkFrame(self, fg_color=COLORS["accent"], height=2, corner_radius=0)
        accent_bar.pack(fill="x", padx=16, pady=(6, 12))


class YouTubeTab:
    """Builds the YouTube URLs tab content inside a given tab frame."""

    def __init__(self, tab, download_command):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        controls_frame = customtkinter.CTkFrame(tab, fg_color="transparent")
        controls_frame.grid(row=0, column=0, padx=4, pady=(4, 4), sticky="ew")

        self.lang_var = customtkinter.StringVar(value="Spanish + English")
        lang_dropdown = LabeledDropdown(
            controls_frame,
            label_text="Language:",
            variable=self.lang_var,
            values=list(LANGUAGE_PRESETS.keys()),
            dropdown_width=200,
        )
        lang_dropdown.pack(side="left")
        self.lang_dropdown = lang_dropdown.dropdown

        self.download_btn = PrimaryButton(
            controls_frame, text="Download Transcripts", command=download_command
        )
        self.download_btn.pack(side="right", padx=(8, 4))

        url_section = SectionTextbox(tab, label_text="PASTE YOUTUBE URLS")
        url_section.grid(row=1, column=0, rowspan=2, padx=0, pady=0, sticky="nsew")
        self.url_textbox = url_section.textbox


class LocalFilesTab:
    """Builds the Local Files tab content inside a given tab frame."""

    def __init__(self, tab, select_files_command, transcribe_command):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        controls_frame = customtkinter.CTkFrame(tab, fg_color="transparent")
        controls_frame.grid(row=0, column=0, padx=4, pady=(4, 4), sticky="ew")

        self.select_files_btn = SecondaryButton(
            controls_frame, text="Select Files", width=120, command=select_files_command
        )
        self.select_files_btn.pack(side="left", padx=(4, 8))

        self.whisper_model_var = customtkinter.StringVar(value="base")
        model_dropdown = LabeledDropdown(
            controls_frame,
            label_text="Model:",
            variable=self.whisper_model_var,
            values=[s.value for s in WhisperModelSize],
            dropdown_width=100,
        )
        model_dropdown.pack(side="left")
        self.whisper_model_dropdown = model_dropdown.dropdown

        self.whisper_lang_var = customtkinter.StringVar(value="Spanish (es)")
        lang_dropdown = LabeledDropdown(
            controls_frame,
            label_text="Language:",
            variable=self.whisper_lang_var,
            values=list(WHISPER_LANGUAGES.keys()),
            dropdown_width=160,
        )
        lang_dropdown.pack(side="left")
        self.whisper_lang_dropdown = lang_dropdown.dropdown

        self.transcribe_btn = PrimaryButton(
            controls_frame, text="Transcribe", command=transcribe_command
        )
        self.transcribe_btn.pack(side="right", padx=(8, 4))

        files_section = SectionTextbox(tab, label_text="SELECTED FILES", textbox_state="disabled")
        files_section.grid(row=1, column=0, rowspan=2, padx=0, pady=0, sticky="nsew")
        self.files_textbox = files_section.textbox


class OptionsPanel(customtkinter.CTkFrame):
    """Shared options panel (timestamps checkbox)."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=10, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self.timestamps_var = customtkinter.BooleanVar(value=False)
        self.timestamps_check = AppCheckbox(
            self, text="Include timestamps [HH:MM:SS]", variable=self.timestamps_var
        )
        self.timestamps_check.grid(row=0, column=0, padx=14, pady=10, sticky="w")


class OutputFolderPanel(customtkinter.CTkFrame):
    """Output folder selection panel."""

    def __init__(self, master, folder_var, browse_command, **kwargs):
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=10, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.folder_selector = FolderSelector(
            self, label_text="Save to:", folder_var=folder_var, browse_command=browse_command
        )
        self.folder_selector.grid(row=0, column=0, sticky="ew")

    @property
    def browse_btn(self):
        return self.folder_selector.browse_btn


class StatusLog(customtkinter.CTkFrame):
    """Status log section with label, textbox, and progress bar."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.progress_bar = AppProgressBar(self)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=(4, 6))
        self.progress_bar.set(0)

        SectionLabel(self, text="STATUS").grid(row=1, column=0, padx=4, pady=(8, 4), sticky="sw")

        self.log_textbox = AppTextbox(
            self,
            state="disabled",
            fg_color=COLORS["surface"],
            text_color=COLORS["text_dim"],
            font=FONTS["mono"],
        )
        self.log_textbox.grid(row=2, column=0, sticky="nsew")


class Footer(customtkinter.CTkFrame):
    """App footer with version and author."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", height=28, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            self, text="VanScript v1.1", font=FONTS["mono_sm"], text_color=COLORS["border"]
        ).pack(side="left")

        customtkinter.CTkLabel(
            self, text="by VanDev", font=FONTS["ui_sm_bold"], text_color=COLORS["text_dim"]
        ).pack(side="right")
