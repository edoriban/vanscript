"""Styled UI widgets for VanScript — base components and common combinations."""

import customtkinter

from theme import COLORS, FONTS


# ---------------------------------------------------------------------------
# Base widgets (styled wrappers)
# ---------------------------------------------------------------------------

class AppLabel(customtkinter.CTkLabel):
    def __init__(self, master, text="", **kwargs):
        defaults = {"font": FONTS["ui"], "text_color": COLORS["text_dim"]}
        defaults.update(kwargs)
        super().__init__(master, text=text, **defaults)


class SectionLabel(customtkinter.CTkLabel):
    def __init__(self, master, text="", **kwargs):
        defaults = {"font": FONTS["mono_label"], "text_color": COLORS["text_dim"]}
        defaults.update(kwargs)
        super().__init__(master, text=text, **defaults)


class PrimaryButton(customtkinter.CTkButton):
    def __init__(self, master, text="", **kwargs):
        defaults = {
            "font": FONTS["ui_btn"],
            "height": 36,
            "corner_radius": 10,
            "fg_color": COLORS["accent"],
            "hover_color": COLORS["accent_hover"],
            "text_color": COLORS["bg"],
        }
        defaults.update(kwargs)
        super().__init__(master, text=text, **defaults)


class SecondaryButton(customtkinter.CTkButton):
    def __init__(self, master, text="", **kwargs):
        defaults = {
            "corner_radius": 8,
            "fg_color": COLORS["surface_hi"],
            "hover_color": COLORS["border"],
            "text_color": COLORS["text"],
            "font": FONTS["ui"],
        }
        defaults.update(kwargs)
        super().__init__(master, text=text, **defaults)


class AppDropdown(customtkinter.CTkOptionMenu):
    def __init__(self, master, **kwargs):
        defaults = {
            "fg_color": COLORS["surface_hi"],
            "button_color": COLORS["border"],
            "button_hover_color": COLORS["accent"],
            "dropdown_fg_color": COLORS["surface"],
            "font": FONTS["ui"],
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class AppTextbox(customtkinter.CTkTextbox):
    def __init__(self, master, **kwargs):
        defaults = {
            "wrap": "word",
            "corner_radius": 10,
            "fg_color": COLORS["surface_hi"],
            "text_color": COLORS["text"],
            "border_width": 1,
            "border_color": COLORS["border"],
            "font": FONTS["mono_code"],
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class AppCheckbox(customtkinter.CTkCheckBox):
    def __init__(self, master, text="", **kwargs):
        defaults = {
            "fg_color": COLORS["surface_hi"],
            "hover_color": COLORS["accent"],
            "checkmark_color": COLORS["bg"],
            "font": FONTS["ui"],
            "text_color": COLORS["text"],
        }
        defaults.update(kwargs)
        super().__init__(master, text=text, **defaults)


class AppEntry(customtkinter.CTkEntry):
    def __init__(self, master, **kwargs):
        defaults = {
            "fg_color": COLORS["surface_hi"],
            "border_color": COLORS["border"],
            "text_color": COLORS["text"],
            "font": FONTS["mono"],
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class AppProgressBar(customtkinter.CTkProgressBar):
    def __init__(self, master, **kwargs):
        defaults = {
            "corner_radius": 6,
            "height": 14,
            "fg_color": COLORS["surface"],
            "progress_color": COLORS["accent"],
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


# ---------------------------------------------------------------------------
# Composite widgets (common combinations)
# ---------------------------------------------------------------------------

class LabeledDropdown(customtkinter.CTkFrame):
    """Label + Dropdown packed side-by-side."""

    def __init__(self, master, label_text, variable, values, dropdown_width=200, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        AppLabel(self, text=label_text).pack(side="left", padx=(4, 4))
        self.dropdown = AppDropdown(self, variable=variable, values=values, width=dropdown_width)
        self.dropdown.pack(side="left", padx=(0, 8))


class SectionTextbox(customtkinter.CTkFrame):
    """Section label + textbox stacked vertically."""

    def __init__(self, master, label_text, textbox_state="normal", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        SectionLabel(self, text=label_text).grid(row=0, column=0, padx=8, pady=(4, 2), sticky="w")
        self.textbox = AppTextbox(self, state=textbox_state)
        self.textbox.grid(row=1, column=0, padx=4, pady=(0, 4), sticky="nsew")


class FolderSelector(customtkinter.CTkFrame):
    """Label + entry + browse button in a row."""

    def __init__(self, master, label_text, folder_var, browse_command, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(1, weight=1)

        AppLabel(self, text=label_text).grid(row=0, column=0, padx=(14, 6), pady=10, sticky="w")
        self.entry = AppEntry(self, textvariable=folder_var)
        self.entry.grid(row=0, column=1, padx=(0, 6), pady=10, sticky="ew")
        self.browse_btn = SecondaryButton(self, text="Browse", width=80, command=browse_command)
        self.browse_btn.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="e")
