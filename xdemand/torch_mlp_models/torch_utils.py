from io import BytesIO
from typing import Optional
import logging
from dynaconf import Dynaconf

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader
from torch.utils.data import TensorDataset

# Set up the logger context
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set the logging level

class TorchUtils:
    """
    Utility class for Torch torch_mlp_models.
    """

    @staticmethod
    def create_dataloaders(
            X_train, X_val, X_test, y_train, y_val, y_test,
            batch_size: int = None,
            device: str = "cpu"
    ):
        """
        Create the DataLoader instances (Torch tensors) for the training, validation, and test pandas dataframe.
        """
        # Convert the data to PyTorch tensors
        X_train_tensor = torch.tensor(X_train.values.astype(np.float32)).to(device)
        y_train_tensor = torch.tensor(y_train.values.astype(np.float32)).view(-1, 1).to(device)
        X_val_tensor = torch.tensor(X_val.values.astype(np.float32)).to(device)
        y_val_tensor = torch.tensor(y_val.values.astype(np.float32)).view(-1, 1).to(device)
        X_test_tensor = torch.tensor(X_test.values.astype(np.float32)).to(device)
        y_test_tensor = torch.tensor(y_test.values.astype(np.float32)).view(-1, 1).to(device)
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_dataset = TensorDataset(X_val_tensor, y_val_tensor)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        test_dataset = TensorDataset(X_test_tensor, y_test_tensor)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
        logger.info('Data loaders created')

        return train_loader, val_loader, test_loader, X_train_tensor

    @staticmethod
    def infer(df: pd.DataFrame, model_path, save_path: Optional[str] = None, target_01: bool = True):
        """
        Infer the target values.
        Args:
            data: The feature space.
            model_path: The path to the model.
            save_path: The path to save the predictions.
            target_01: Whether to clip the predictions to [0, 1].

        Returns:
            The predicted target values.
        """
        # Load the PyTorch model from the specified path, check if the model is torchscript
        # check if model path is a string
        if isinstance(model_path, str):
            if model_path.endswith('.pt'):
                model = torch.jit.load(model_path)
            else:
                model = torch.load(model_path)
        model=model_path
        model.eval()
        # Convert to PyTorch tensor
        X = torch.tensor(df.values, dtype=torch.float32)
        logger.info(f"Data shape after encoding: {X.shape}")
        # Load the model
        # Apply the model
        with torch.no_grad():
            outputs = model(X)
        if target_01:
            torch.clamp(outputs, 0, 1, out=outputs)
        # Optionally save or return results
        df['predictions'] = outputs.numpy()
        logger.info("Inference completed.")

        # Save the results
        if save_path:
            df['predictions'].to_csv(save_path, index=False)
            logger.info("Inference completed and saved.")
        return df['predictions'].clip(0, 1)

    @staticmethod
    def get_torch_script_model(model, input_size: int):
        """
        Convert the model to TorchScript.

        Args:
            input_size: The size of the input features.

        Returns:
            The TorchScript model.
        """
        # Ensure your model is in evaluation mode
        model.eval()
        # An example input is required for tracing the model
        example_input = torch.rand(1, input_size)  # X_train.shape[1] gives the number of features
        # Use torch.jit.trace to convert the model
        return torch.jit.trace(model, example_input)

        # Save the TorchScript model
        # traced_script_module.save(path)

    # TODO : check if this is needed. How to write a proper model to S3
    @staticmethod
    def create_torch_trace_output(model: nn.Module, input_size: int,
                                  save_path: str, config: Dynaconf):
        """
        Convert the model to TorchScript and return it.

        Args:
            model: The torch model to convert.
            input_size: The size of the input features.
        """
        # Ensure your model is in evaluation mode
        model.eval()

        device= config['device']
        # An example input is required for tracing the model
        example_input = torch.rand(1, input_size).to(device)  # X_train.shape[1] gives the number of features

        # Use torch.jit.trace to convert the model
        traced_script_module = torch.jit.trace(model, example_input)
        buffer = BytesIO()
        torch.jit.save(traced_script_module, buffer)
        return buffer

    @staticmethod
    def evaluate_last_day_MSE(model: nn.Module, ctr_data: pd.DataFrame, config) -> float:
        """
        Evaluate the model's performance on the last day's data using Mean Squared Error.

        This function is used when prev_day_finetune is True. It processes the last day's data,
        creates test data loaders, and evaluates the model's performance.

        :param model: The trained PyTorch model to evaluate
        :param last_day_data: DataFrame containing the last day's data
        :return: Mean Squared Error (MSE) of the model's predictions on the last day's data
        """
        logger.info("Evaluating model performance on the last day's data...")

        # Ensure we're working with the last day's data only
        last_day = ctr_data['date'].max()
        last_day_data = ctr_data[ctr_data['date'] == last_day]

        # Process the data
        last_day_data = last_day_data.dropna()
        # drop the date column
        last_day_data = last_day_data.drop('date', axis=1)

        # Ensure all columns are of supported types
        last_day_data = last_day_data.astype(np.float32)

        # Separate features (X) and target (y)
        X_test = last_day_data.drop('click_rate', axis=1)
        y_test = last_day_data['click_rate']

        # Create data loader
        x_test_tensor = torch.FloatTensor(X_test.values)
        y_test_tensor = torch.FloatTensor(y_test.values).view(-1, 1)
        test_dataset = TensorDataset(x_test_tensor, y_test_tensor)
        test_loader = DataLoader(test_dataset, batch_size=len(last_day_data), shuffle=False)

        # Set the model to evaluation mode
        model.eval()

        # move the model to device
        model.to(config['device'])
        # Evaluate the model
        criterion = nn.MSELoss()
        test_loss = model.evaluate(test_loader, criterion, config)

        logger.info(f"Last day MSE: {test_loss:.6f}")

        return test_loss