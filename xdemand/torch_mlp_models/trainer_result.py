from dataclasses import dataclass
from typing import Any

from torch import nn as nn


@dataclass
class TrainerResult:
    """
    The result contains the result of the model training.
    This includes the trained model, the state of the best model and the validation loss of the best model.
    """
    model: nn.Module
    best_model_state: Any
    val_loss: float
    test_loss: float
    input_size: int
