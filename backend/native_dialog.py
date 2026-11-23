"""Diálogos nativos para PIN e arquivos de credenciais ou intercâmbio."""

import re
import sys
from datetime import datetime
from pathlib import Path


class NativeDialogError(RuntimeError):
    """O diálogo nativo foi cancelado ou não pôde ser apresentado."""


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


def collect_pin(title: str, prompt: str = "Informe o PIN local:") -> str:
    """Coleta o PIN apenas pelo diálogo nativo, sem passá-lo ao navegador."""
    root = _root()
    try:
        from tkinter import simpledialog

        pin = simpledialog.askstring(title, prompt, parent=root, show="*")
        if not pin or not pin.isdigit() or not 4 <= len(pin) <= 6:
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
