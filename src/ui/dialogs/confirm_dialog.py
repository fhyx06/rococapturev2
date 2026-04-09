"""确认弹窗与新建存档弹窗"""
import customtkinter as ctk


class ConfirmDialog(ctk.CTkToplevel):
    """通用的确认/取消弹窗"""

    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = False
        self.grab_set()

        # 居中于父窗口
        self.transient(parent)
        self.geometry(
            f"+{parent.winfo_rootx() + parent.winfo_width() // 2 - 150}"
            f"+{parent.winfo_rooty() + parent.winfo_height() // 2 - 60}"
        )

        # 内容
        pad = 20
        frame = ctk.CTkFrame(self)
        frame.pack(padx=pad, pady=pad)

        ctk.CTkLabel(frame, text=message, wraplength=250).pack(pady=(10, 15))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(
            btn_frame, text="取消", width=80,
            command=self._on_cancel,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="确认", width=80,
            fg_color="#e74c3c", hover_color="#c0392b",
            command=self._on_confirm,
        ).pack(side="left", padx=5)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    def _on_confirm(self):
        self.result = True
        self.destroy()

    def _on_cancel(self):
        self.result = False
        self.destroy()


class CreateSaveDialog(ctk.CTkToplevel):
    """新建存档弹窗"""

    def __init__(self, parent, existing_names: list[str] | None = None):
        super().__init__(parent)
        self.title("新建存档")
        self.resizable(False, False)
        self.result: str | None = None
        self._existing = set(existing_names or [])
        self.grab_set()

        self.transient(parent)
        self.geometry(
            f"+{parent.winfo_rootx() + parent.winfo_width() // 2 - 150}"
            f"+{parent.winfo_rooty() + parent.winfo_height() // 2 - 60}"
        )

        pad = 20
        frame = ctk.CTkFrame(self)
        frame.pack(padx=pad, pady=pad)

        ctk.CTkLabel(frame, text="请输入存档名称：").pack(pady=(10, 5))

        self._entry = ctk.CTkEntry(frame, width=250, placeholder_text="例如：主账号")
        self._entry.pack(pady=5)
        self._entry.bind("<Return>", lambda e: self._on_confirm())
        self._entry.focus_set()

        self._error_label = ctk.CTkLabel(frame, text="", text_color="#e74c3c")
        self._error_label.pack()

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(5, 10))

        ctk.CTkButton(btn_frame, text="取消", width=80, command=self._on_cancel).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="创建", width=80, command=self._on_confirm).pack(side="left", padx=5)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    def _on_confirm(self):
        name = self._entry.get().strip()
        if not name:
            self._error_label.configure(text="名称不能为空")
            return
        # 去掉文件名非法字符
        import re
        safe = re.sub(r'[<>:"/\\|?*]', "", name)
        if not safe:
            self._error_label.configure(text="名称包含非法字符")
            return
        if safe in self._existing:
            self._error_label.configure(text="该存档名已存在")
            return
        self.result = safe
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()
