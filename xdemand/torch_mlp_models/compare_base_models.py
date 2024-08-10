import logging
import pandas as pd
import numpy as np
import importlib
from typing import Dict, Any
from ctr_predictor.metrics.error import ErrorComputer
from ctr_predictor.logging.mlflow import MLflowLogger
import mlflow

logger = logging.getLogger(__name__)

class BaselineModelComparator:
    def __init__(self, baseline_model_name: str,
                 model_params: Dict[str, Any] = None,
                 mlflow: MLflowLogger = None,
                 target_01: bool = True):
        """
        Initialize the BaseModelComparator with the specified base model.

        Args:
            base_model_name (str): Name of the base model (e.g., 'LinearRegression', 'Ridge', 'XGBRegressor').
            base_model_params (Dict[str, Any]): Parameters for the base model.
            target_01 (bool): Whether to clip the target values to [0, 1].
        """
        self.baseline_model_name = baseline_model_name
        self.model_params = model_params if model_params is not None else {}
        self.target_01 = target_01
        self.base_model = self._get_base_model()
        self.mlflow = mlflow

    def _get_base_model(self):
        """
        Dynamically import and instantiate the base model.

        Returns:
            An instance of the specified base model.
        """
        try:
            module_name, class_name = self.baseline_model_name.rsplit('.', 1)
            module = importlib.import_module(module_name)
            base_model_class = getattr(module, class_name)
            return base_model_class(**self.model_params)
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing {self.baseline_model_name}: {e}")
            raise

    def compare_base_model(self,
                           x_train: pd.DataFrame, x_val: pd.DataFrame, x_test: pd.DataFrame,
                           y_train: pd.Series, y_val: pd.Series, y_test: pd.Series) -> None:
        """
        Train the base model and compare its performance.

        Args:
            x_train (pd.DataFrame): Training features.
            x_val (pd.DataFrame): Validation features.
            x_test (pd.DataFrame): Test features.
            y_train (pd.Series): Training targets.
            y_val (pd.Series): Validation targets.
            y_test (pd.Series): Test targets.
        """
        # Dynamically import and instantiate the base model
        module_name, class_name = self.baseline_model_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        base_model_class = getattr(module, class_name)
        base_model = base_model_class(**self.model_params)


        # Combine training and validation sets
        x_train_full = pd.concat([x_train, x_val])
        y_train_full = pd.concat([y_train, y_val])

        # Initialize and train the base model
        base_model.fit(x_train_full, y_train_full)

        # Predict on training and test sets
        y_train_pred = base_model.predict(x_train_full)
        y_test_pred = base_model.predict(x_test)

        # Clip the outputs to the range [0, 1] if target_01 is True
        if self.target_01:
            y_train_pred = np.clip(y_train_pred, 0, 1)
            y_test_pred = np.clip(y_test_pred, 0, 1)

        # Calculate MSE for training and test sets
        train_mse = ErrorComputer(y_train_full, y_train_pred).mean_squared_error()
        test_mse = ErrorComputer(y_test, y_test_pred).mean_squared_error()

        # Log results
        logger.info(f"Training MSE for {self.baseline_model_name}: {train_mse}")
        logger.info(f"Test MSE for {self.baseline_model_name}: {test_mse}")

        _, class_name = self.baseline_model_name.rsplit('.', 1)
        # Log to MLflow
        self.mlflow.log_metric(f"{class_name}_train_mse", train_mse)
        self.mlflow.log_metric(f"{class_name}_test_mse", test_mse)
        return