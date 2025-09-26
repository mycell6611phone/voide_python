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
