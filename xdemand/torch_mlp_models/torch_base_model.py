import logging
from typing import Optional, Union, Tuple

import numpy as np
import torch
from torch import nn, optim
from torch.nn.modules import loss as ls
from torch.utils.data import DataLoader

from ctr_predictor.io.s3writer import ModelS3Writer
from ctr_predictor.logging.mlflow import MLflowLogger
from torch.optim.lr_scheduler import ReduceLROnPlateau
from ctr_predictor.models.trainer_result import TrainerResult

# Set up the logger context
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set the logging level

# Type hint for loss functions
# Create the list of types first
LossTypes = [getattr(ls, name) for name in ls.__all__]
# Then pass it to Union
LossType = Union[tuple(LossTypes)]


class TorchBaseModel(nn.Module):
    """
    Base class for Torch torch_mlp_models. It provides the basic functionality to train, predict and evaluate a model.
    """

    def __init__(self):
        super(TorchBaseModel, self).__init__()

    def train_model(self,
                    train_loader: DataLoader,
                    val_loader: DataLoader,
                    test_loader: DataLoader,
                    criterion: nn.modules.loss._Loss,
                    optimizer: optim.Optimizer,
                    epochs: int,
                    mlflow_logger: Optional[MLflowLogger] = None,
                    config=None,
                    device='cpu',
                    target_01=True
                    ) -> TrainerResult:
        model = self
        best_val_loss = float('inf')
        best_test_loss = float('inf')
        best_model_state = None

        # Initialize the scheduler based on the config
        scheduler = None
        if config['lr_scheduler']['use_scheduler']:
            scheduler_params = config['lr_scheduler']['parameters']
            scheduler = ReduceLROnPlateau(optimizer, mode='min', **scheduler_params)

        for epoch in range(epochs):
            # Training phase
            model.train()
            for batch in train_loader:
                inputs, targets = batch
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                if target_01:
                    outputs = torch.clamp(outputs, 0, 1)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            # Evaluation phase
            train_loss = model.evaluate(train_loader, criterion, config, device)
            val_loss = model.evaluate(val_loader, criterion, config,device)
            test_loss = model.evaluate(test_loader, criterion, config,device)

            # Step the scheduler if it's being used
            if scheduler:
                scheduler.step(val_loss)  # Using validation loss to step the scheduler

            # Log the current learning rate
            current_lr = optimizer.param_groups[0]['lr']
            mlflow_logger.log_metric('learning_rate', current_lr, step=epoch)
            logger.info(f'Epoch {epoch + 1}/{epochs} - Learning rate: {current_lr}')

            # Log the metrics
            logger.info(f'Epoch {epoch + 1}/{epochs} - Train loss: {train_loss}')
            logger.info(f'Epoch {epoch + 1}/{epochs} - Validation loss: {val_loss}')
            logger.info(f'Epoch {epoch + 1}/{epochs} - Test loss: {test_loss}')

            # Log the metrics to MLflow
            if mlflow_logger:
                mlflow_logger.log_metric('train_loss', train_loss, step=epoch)
                mlflow_logger.log_metric('val_loss', val_loss, step=epoch)
                mlflow_logger.log_metric('test_loss', test_loss, step=epoch)

            # Track the best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_test_loss = test_loss
                best_model_state = model.state_dict()
                logger.info(f'Checkpoint at epoch {epoch + 1} with validation loss: {best_val_loss}')

        X_train_tensor = next(iter(train_loader))[0]
        trainer_result = TrainerResult(model, best_model_state, best_val_loss, best_test_loss, X_train_tensor.shape[1])
        return trainer_result

    def predict(self, test_loader: DataLoader, device='cpu', target_01= True) -> np.ndarray:
        """
        Predict the target values.

        Args:
            test_loader (DataLoader): The DataLoader instance of the feature space.
            device: device
            target_01 (bool): Whether to clip the target values to [0, 1].


        Returns:
            np.ndarray: Predicted values.
        """
        model = self
        model.eval()
        with torch.no_grad():
            predictions = []
            for data, _ in test_loader:
                data = data.to(device)
                output = model(data)
                predictions.extend(output.cpu().numpy())
        predictions = np.array(predictions)
        # Clip the predictions to the range [0, 1]
        if target_01:
            predictions = np.clip(predictions, 0, 1)
        return predictions

    def evaluate(self, loader: DataLoader,
                 criterion: LossType,
                 config,
                 device='cpu',
                 target_01=True) -> float:
        """
        Evaluate the model.

        Args:
            loader (DataLoader): The DataLoader instance of the feature space.
            criterion (LossType): The loss function to use for evaluation.
            config: Configuration dictionary.
            target_01 (bool): Whether to clip the target values to [0, 1].

        Returns:
            float: The total loss based on the criterion.
        """
        model = self
        model.eval()
        total_loss = 0
        with torch.no_grad():
            for data, target in loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                # Clip the output to the range [0, 1]
                if target_01:
                    output = torch.clamp(output, 0, 1)
                loss = criterion(output, target)
                total_loss += loss.item()
        return total_loss / len(loader)