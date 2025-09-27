from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

class ChatWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_send: Callable[[str], None]):
        super().__init__(master)
        self.title("VOIDE Chat")
        self.geometry("480x420")
        self.on_send = on_send

        self.out = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=18)
        self.out.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        frm = tk.Frame(self)
        frm.pack(fill=tk.X, padx=6, pady=6)
        self.entry = tk.Entry(frm)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self._send)
        tk.Button(frm, text="Send", command=self._send).pack(side=tk.LEFT, padx=4)

        # Ensure closing the window only hides it so it can be toggled back with a click.
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.bind("<Escape>", self.hide)
        self.after(10, self._focus_entry)

    def _send(self, *_):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self.append_user(text)
        self.on_send(text)

    def append_user(self, text: str):
        self.out.insert(tk.END, f"You: {text}\n")
        self.out.see(tk.END)

    def append_assistant(self, text: str):
        self.out.insert(tk.END, f"Assistant: {text}\n")
        self.out.see(tk.END)

    def _focus_entry(self) -> None:
        try:
            self.entry.focus_set()
        except tk.TclError:
            pass

    def show(self) -> None:
        """Make the chat window visible and focused."""

        self.deiconify()
        try:
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass
        self._focus_entry()

    def hide(self, *_event) -> None:
        """Hide the chat window without destroying it."""

        try:
            self.withdraw()
        except tk.TclError:
            pass
        parent = getattr(self, "master", None)
        if parent is not None:
            try:
                parent.focus_force()
            except tk.TclError:
                pass

    def toggle(self) -> None:
        """Toggle between visible and hidden states."""

        try:
            state = self.state()
        except tk.TclError:
            state = "withdrawn"
        if state == "withdrawn":
            self.show()
        else:
            self.hide(None)
