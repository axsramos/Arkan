"""Contrato interno de preparação para uma ativação futura.

Este módulo não cria persistência e não manipula identidade, PIN ou chaves.
"""

from dataclasses import dataclass
from pathlib import Path

from backend.config import STORAGE_DIR, storage_is_activated


class ActivationStateError(RuntimeError):
    """A cópia já possui estado ativado e não pode ser ativada novamente."""


@dataclass(frozen=True)
class ActivationPreparation:
    """Referência efêmera ao destino que a transação de ativação poderá usar."""

    storage_dir: Path


def prepare_activation(storage_dir: Path | str = STORAGE_DIR) -> ActivationPreparation:
    """Prepara o contrato de ativação sem criar diretório ou qualquer arquivo."""
    target = Path(storage_dir)
    if storage_is_activated(target):
        raise ActivationStateError("Esta cópia já possui uma ativação confirmada.")
    return ActivationPreparation(storage_dir=target)
