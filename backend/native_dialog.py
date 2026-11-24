"""Diálogos nativos para PIN e arquivos de credenciais ou intercâmbio."""

import re
import sys
from datetime import datetime
from pathlib import Path


class NativeDialogError(RuntimeError):
    """O diálogo nativo foi cancelado ou não pôde ser apresentado."""


_PIN_BACKGROUND = "#020617"
_PIN_SURFACE = "#0f172a"
_PIN_BORDER = "#1e293b"
_PIN_ACCENT = "#22d3ee"
_PIN_TEXT = "#e2e8f0"
_PIN_MUTED_TEXT = "#94a3b8"


def _root():
    if sys.platform != "win32":
        raise NativeDialogError("Diálogo nativo indisponível nesta plataforma.")
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        return root
    except Exception as error:
        raise NativeDialogError("Diálogo nativo indisponível.") from error


def _is_valid_pin(pin: str | None) -> bool:
    """Valida o formato do PIN sem registrá-lo nem expô-lo."""
    return isinstance(pin, str) and pin.isdigit() and 4 <= len(pin) <= 6


class _PinDialog:
    """Coleta o PIN no processo local com a identidade visual do Arkan."""

    def __init__(self, root, title: str, prompt: str):
        import tkinter as tk

        self._result: str | None = None
        self._value = tk.StringVar()
        self._feedback = tk.StringVar()
        self._window = tk.Toplevel(root, bg=_PIN_BACKGROUND)
        self._window.title(title)
        self._window.resizable(False, False)
        self._window.transient(root)
        self._window.attributes("-topmost", True)
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

        panel = tk.Frame(self._window, bg=_PIN_SURFACE, highlightbackground=_PIN_BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(panel, text="ARKAN", bg=_PIN_SURFACE, fg=_PIN_ACCENT, font=("Segoe UI", 16, "bold")).pack(pady=(24, 4))
        tk.Label(panel, text="Proteção local", bg=_PIN_SURFACE, fg=_PIN_MUTED_TEXT, font=("Segoe UI", 9)).pack()
        tk.Label(panel, text=prompt, bg=_PIN_SURFACE, fg=_PIN_TEXT, font=("Segoe UI", 11), wraplength=340, justify="center").pack(padx=28, pady=(22, 12))

        self._entry = tk.Entry(
            panel,
            textvariable=self._value,
            show="•",
            bg=_PIN_BACKGROUND,
            fg=_PIN_TEXT,
            insertbackground=_PIN_TEXT,
            highlightbackground=_PIN_BORDER,
            highlightcolor=_PIN_ACCENT,
            highlightthickness=1,
            relief="flat",
            justify="center",
            font=("Segoe UI", 16),
            width=18,
        )
        self._entry.pack(ipady=9, padx=36)
        tk.Label(panel, textvariable=self._feedback, bg=_PIN_SURFACE, fg="#fca5a5", font=("Segoe UI", 9)).pack(pady=(8, 0))

        actions = tk.Frame(panel, bg=_PIN_SURFACE)
        actions.pack(fill="x", padx=28, pady=(14, 24))
        tk.Button(actions, text="Cancelar", command=self._cancel, bg=_PIN_SURFACE, fg=_PIN_TEXT, activebackground=_PIN_BORDER, activeforeground=_PIN_TEXT, borderwidth=0, font=("Segoe UI", 10), padx=14, pady=8).pack(side="left")
        tk.Button(actions, text="Continuar", command=self._submit, bg=_PIN_ACCENT, fg=_PIN_BACKGROUND, activebackground="#67e8f9", activeforeground=_PIN_BACKGROUND, borderwidth=0, font=("Segoe UI", 10, "bold"), padx=18, pady=8).pack(side="right")

        self._window.bind("<Return>", self._submit)
        self._window.bind("<Escape>", self._cancel)
        self._window.update_idletasks()
        self._window.geometry(f"420x280+{(self._window.winfo_screenwidth() - 420) // 2}+{(self._window.winfo_screenheight() - 280) // 2}")
        self._window.grab_set()
        self._entry.focus_set()

    def show(self) -> str | None:
        self._window.wait_window()
        return self._result

    def _submit(self, _event=None) -> None:
        pin = self._value.get()
        if not _is_valid_pin(pin):
            self._feedback.set("Use um PIN de 4 a 6 dígitos.")
            self._entry.focus_set()
            return
        self._result = pin
        self._window.destroy()

    def _cancel(self, _event=None) -> None:
        self._result = None
        self._window.destroy()


def collect_pin(title: str, prompt: str = "Informe o PIN local:") -> str:
    """Coleta o PIN apenas pelo diálogo nativo, sem passá-lo ao navegador."""
    root = _root()
    try:
        pin = _PinDialog(root, title, prompt).show()
        if not _is_valid_pin(pin):
            raise NativeDialogError("Coleta de PIN cancelada ou inválida.")
        return pin
    finally:
        root.destroy()


def collect_new_pin() -> str:
    """Coleta duas vezes o novo PIN no canal nativo e confirma a igualdade."""
    pin = collect_pin("Definir PIN do Arkan", "Defina um PIN de 4 a 6 dígitos:")
    confirmation = collect_pin("Confirmar PIN do Arkan", "Repita o PIN de 4 a 6 dígitos:")
    if pin != confirmation:
        raise NativeDialogError("Os PINs informados não coincidem.")
    return pin


def _save(artifact: bytes, title: str, extension: str, label: str, suggested_name: str | None = None) -> None:
    root = _root()
    try:
        from tkinter import filedialog

        selected = filedialog.asksaveasfilename(
            title=title,
            defaultextension=extension,
            filetypes=((label, f"*{extension}"),),
            initialfile=suggested_name,
            parent=root,
        )
        if not selected:
            raise NativeDialogError("Salvamento do arquivo cancelado.")
        Path(selected).write_bytes(artifact)
    except NativeDialogError:
        raise
    except OSError as error:
        raise NativeDialogError("Não foi possível salvar o arquivo selecionado.") from error
    finally:
        root.destroy()


def _collect(title: str, extension: str, label: str) -> bytes:
    root = _root()
    try:
        from tkinter import filedialog

        selected = filedialog.askopenfilename(title=title, filetypes=((label, f"*{extension}"), ("Todos os arquivos", "*.*")), parent=root)
        if not selected:
            raise NativeDialogError("Seleção de arquivo cancelada.")
        return Path(selected).read_bytes()
    except NativeDialogError:
        raise
    except OSError as error:
        raise NativeDialogError("Não foi possível ler o arquivo selecionado.") from error
    finally:
        root.destroy()


def save_recovery_credential(artifact: bytes) -> None:
    """Salva `ARKR v2` no caminho escolhido localmente pela pessoa."""
    _save(artifact, "Salvar credencial de recuperação do Arkan", ".arkr", "Credencial de recuperação Arkan", "recovery.arkr")


def collect_recovery_credential() -> bytes:
    """Seleciona `ARKR v2` sem expor caminho ou conteúdo ao frontend."""
    return _collect("Selecionar credencial de recuperação do Arkan", ".arkr", "Credencial de recuperação Arkan")


def save_invitation_artifact(artifact: bytes) -> None:
    """Entrega `ARKI v2` somente pelo seletor nativo local."""
    _save(artifact, "Salvar ingresso do Arkan", ".arki", "Ingresso Arkan", "invite.arki")


def collect_invitation_artifact() -> bytes:
    """Coleta `ARKI v2` sem expor caminho ou conteúdo ao frontend."""
    return _collect("Selecionar ingresso do Arkan", ".arki", "Ingresso Arkan")


def save_export_artifact(artifact: bytes, pseudonym: str) -> None:
    """Entrega `ARKX v2` somente pelo seletor nativo local."""
    safe_pseudonym = re.sub(r"[^A-Za-z0-9_-]+", "-", pseudonym.strip()).strip("-") or "membro"
    filename = f"{datetime.now().strftime('%Y%m%d%H%M')}-{safe_pseudonym}.arkx"
    _save(artifact, "Salvar exportação do Arkan", ".arkx", "Exportação Arkan", filename)


def collect_export_artifact() -> bytes:
    """Coleta `ARKX v2` sem expor caminho ou conteúdo ao frontend."""
    return _collect("Selecionar exportação do Arkan", ".arkx", "Exportação Arkan")


def select_attachment_path() -> Path:
    """Seleciona anexo local sem expor caminho à interface web."""
    root = _root()
    try:
        from tkinter import filedialog

        selected = filedialog.askopenfilename(title="Selecionar anexo do artigo", parent=root)
        if not selected:
            raise NativeDialogError("Seleção de anexo cancelada.")
        return Path(selected)
    finally:
        root.destroy()
