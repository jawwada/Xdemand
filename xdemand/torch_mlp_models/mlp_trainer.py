import logging
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

import pandas as pd
import pytz
import torch
import torch.nn as nn
import torch.optim as optim
from dynaconf import Dynaconf

from ctr_predictor.data_operator.ctr_data_processor import CTRDataProcessor
from ctr_predictor.logging.mlflow import MLflowLogger
from ctr_predictor.metrics.error import ErrorComputer
from ctr_predictor.models.compare_base_models import BaselineModelComparator
from ctr_predictor.models.log_edge_cases import analyze_model_edge_cases
from ctr_predictor.models.torch_mlp_xl import MLP_XL
from ctr_predictor.models.torch_utils import TorchUtils
from ctr_predictor.models.trainer_result import TrainerResult
from ctr_predictor.visualization.model_performance import Scatter

# Set up the logger context
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set the logging level


class MLPTrainer:
    """

    Attributes:
        ctr_data_frame: dataframe with the CTR data
        run_dt: run date
        past_days:  number of past days to consider for training
        mlflow_uri: URI for the MLflow tracking server
        network_id: network ID
        config: configuration dictionary for the MLP model
    """

    def __init__(self, ctr_data_frame: pd.DataFrame,
                 run_dt: str, # TODO: This date should be a datetime.date object. If conversion is needed do it within the class.
                 mlflow_uri: str,
                 past_days: int,
                 network_id: int,
                 config: Dynaconf,
                 past_model: Optional[Dict[Any, Any]] = None,
                 cli_dict: Optional[Dict[str, Any]] = None
                 ):

        self.ctr_data_frame = ctr_data_frame
        self.run_dt = run_dt
        self.past_days = past_days
        self.past_model = past_model
        self.network_id = network_id
        self.config = config
        self.device = torch.device(self.config["torch_mlp"]["device"])
        self.mlflow_uri = mlflow_uri
        self.cli_dict =  {
            "run_dt": run_dt,
            "past_days": past_days,
            "network_id": network_id,
        } if cli_dict is None else deepcopy(cli_dict)
        experiment_name = f"Network_ID={self.network_id}"
        self.mlflow = MLflowLogger(mlflow_uri, experiment_name)
        self.last_day_mse = None

    def build_and_train_model(self) -> TrainerResult:
        """
        Builds and trains the MLP model, evaluates its performance, and saves the model to a local path or S3 bucket.
        """
        logger.info("Starting model training...")
        # Set the random seed if needed
        torch_random_seed = self.config['torch_mlp']['torch_random_seed']
        if torch_random_seed is not None:
            torch.manual_seed(torch_random_seed)


        # Process the data
        self.ctr_data_frame['date'] = pd.to_datetime(self.ctr_data_frame['date'])
        # extract past date from run_dt-past_days to run_dt
        # convert run_dt to datetime object
        past_date = datetime.strptime(self.run_dt, '%Y-%m-%d') - timedelta(days=self.past_days)
        utc_time_zone = pytz.timezone('UTC')
        past_date = utc_time_zone.localize(past_date)
        self.ctr_data_frame = self.ctr_data_frame[self.ctr_data_frame['date'] >= past_date]
        self.ctr_data_frame = self.ctr_data_frame[self.ctr_data_frame['date'] <= self.run_dt]
        # TODO: Discuss How to merge the identical operations of prev 4 lines and function below
        self.ctr_data_frame = self.ensure_datetime_compatibility(self.ctr_data_frame,
                                                                 'date',
                                                                 self.past_days,
                                                                 self.run_dt)

        ctr_data_frame_matrix = CTRDataProcessor.get_pretensor_df(self.ctr_data_frame)
        ctr_data_frame_matrix = ctr_data_frame_matrix.dropna()
        x_train, x_val, x_test, y_train, y_val, y_test = CTRDataProcessor.get_test_train_validation_sets(
            ctr_data_frame_matrix,
            test_size=self.config['data_split']["test_size"],
            test_val_size=self.config['data_split']["test_val_size"],
            random_seed_split=self.config['data_split']["random_seed_split"]
        )
        train_loader, val_loader, test_loader, x_train_tensor = (
            TorchUtils.create_dataloaders(x_train, x_val, x_test, y_train, y_val, y_test,
                                          self.config['torch_mlp']["batch_size"],
                                          self.config["torch_mlp"]["device"])
        )
        model_parameters=self.config['torch_mlp']['mlp_parameters']
        # Initialize model, loss, and optimizer
        mlp_obj = MLP_XL(
            input_size=x_train.shape[1],
            hidden_layer_sizes=model_parameters["hidden_layer_sizes"],
            activation=model_parameters["activation"],
            dropout_rate=model_parameters["dropout_rate"],
            use_attention=model_parameters["use_attention"],
            output_activation=model_parameters["output_activation"],
            config=model_parameters
        ).to(self.device)

        if self.past_model is not None:
            mlp_obj, _, _ = self.prepare_model_from_checkpoint(mlp_obj, self.past_model)
            self.last_day_mse = TorchUtils.evaluate_last_day_MSE(mlp_obj, self.ctr_data_frame, self.config)

        optimizer_params = self.config['torch_mlp']['torch_optimizer']
        # import criterion dynamically based on the config['optimizer']['criterion']
        criterion = getattr(nn, optimizer_params['criterion'])()
        optimizer = optim.Adam(mlp_obj.parameters(), **optimizer_params['Adam'])

        # Start MLflow run with model name and log parameters
        # run name is same as run_dt string
        now_utc = datetime.now(tz=timezone.utc)
        run_name = f"Run of {self.run_dt}@{now_utc.isoformat()}"


        with self.mlflow.start_run(run_name):
            # Train the model and save the best model
            training_result = mlp_obj.train_model(
                train_loader,
                val_loader,
                test_loader,
                criterion,
                optimizer,
                self.config["torch_mlp"]["epochs"],
                mlflow_logger=self.mlflow,
                config=optimizer_params,
                device=self.device
            )
            logger.info("Model training completed successfully!")
            model = training_result.model
            best_val_loss = training_result.val_loss
            best_test_loss = training_result.test_loss
            analyze_model_edge_cases(model, training_result.input_size, self.mlflow)
            error_compute=ErrorComputer(x_test['previous_week_rate'],y_test)
            previous_week_mse=error_compute.mean_squared_error()

            # Build compare baseline model
            base_model_comparator = BaselineModelComparator(
                baseline_model_name=self.config['baseline_model']['baseline_name'],
                model_params=self.config['baseline_model'].get('baseline_params', {}),
                mlflow=self.mlflow,
                target_01=self.config['baseline_model'].get('target_01', True)
            )
            # Compare the base model and get the results
            base_model_comparator.compare_base_model(x_train, x_val, x_test, y_train, y_val, y_test)

            self.log_mlp_mlflow(mlp_obj=model,
                                y_test=y_test,
                                test_loader=test_loader,
                                input_size=x_train_tensor.shape[1],
                                best_val_loss=best_val_loss,
                                best_test_loss=best_test_loss,
                                previous_week_mse=previous_week_mse,
                                last_day_mse=self.last_day_mse,
                                config=self.config)
            logger.info("Model training completed successfully!")


            return training_result

    def log_mlp_mlflow(self, mlp_obj,
                       y_test,
                       test_loader,
                       input_size: int,
                       best_val_loss: float,
                       best_test_loss:float,
                       previous_week_mse: float,
                       last_day_mse: float,
                       config: Dynaconf) -> None:
        """
        Log the MLP model to MLflow.

        Args:
            mlp_obj: The MLP model object.
            y_test: The test target values.
            test_loader: The test data loader.
            input_size: The input size of the model.
            best_val_loss: The best validation loss.
            best_test_loss: The best test loss.
            previous_week_mse: The MSE of the previous week.
            last_day_mse: The MSE of the last day.
            config: The configuration dictionary.
        """
        logger.info("Mlflow Logging the model, parameters and results...")
        # Log the params_dict to MLflow
        self.mlflow.log_params(self.cli_dict)
        self.mlflow.log_params({'input_size': input_size})
        # save model to MLflow
        mlp_obj.eval()
        traced_script_module = torch.jit.trace(mlp_obj, torch.rand(1, input_size))
        with tempfile.NamedTemporaryFile(suffix='.pt') as tmpfile:
            torch.jit.save(traced_script_module, tmpfile.name)
            tmpfile.seek(0)
            self.mlflow.log_artifact(tmpfile.name)
        logger.info("Model saved to MLflow.")
        # Plot the scatter plot for the model, using the test_loader
        error_scatter_plot = Scatter(y_test, mlp_obj.predict(test_loader, self.device))
        error_scatter_plot.plot(mlp_obj.__class__.__name__)
        self.mlflow.log_figures([error_scatter_plot.get_fig_object()], ["Test-prediction scatter plot"])
        logger.info("Model scatter plot logged to MLflow.")

        # Log model parameters to MLflow
        self.mlflow.log_params(config)
        # Log the model architecture
        # Log the best validation loss
        self.mlflow.log_metric('best_val_loss', best_val_loss)
        self.mlflow.log_metric('best_test_loss', best_test_loss)
        self.mlflow.log_metric('previous_week_mse', previous_week_mse)
        # log the previous day's MSE if it is not None
        if last_day_mse:
            self.mlflow.log_metric('last_day_mse', last_day_mse)
        logger.info("Model parameters and results logged to MLflow.")
        return

    @staticmethod
    def prepare_model_from_checkpoint(model: nn.Module, checkpoint: dict):
        """
        Prepare the model from the given checkpoint.

        Args:
            model: The model object.
            checkpoint: The checkpoint dictionary.

        Returns:
            nn.Module: The prepared model.
        """
        # Get the input size and model parameters from the checkpoint
        input_size = checkpoint['input_size']
        model_params = checkpoint['model_parameters']
        # Load the state dictionary into the model
        model.load_state_dict(checkpoint['model_state_dict'])
        return model, input_size, model_params

    @staticmethod
    def ensure_datetime_compatibility(df: pd.DataFrame, date_column: str, past_days: int, run_dt: str) -> pd.DataFrame:
        # Convert run_dt to datetime
        run_dt = pd.to_datetime(run_dt)

        # Convert the date column to datetime
        df[date_column] = pd.to_datetime(df[date_column])

        # Ensure both are timezone-naive or timezone-aware
        if run_dt.tzinfo is None:
            df[date_column] = df[date_column].dt.tz_localize(None)
        else:
            df[date_column] = df[date_column].dt.tz_convert(run_dt.tzinfo)

        # Calculate past_date
        past_date = run_dt - timedelta(days=past_days)
        if run_dt.tzinfo is not None:
            past_date = past_date.tz_localize(run_dt.tzinfo)

        # Filter the DataFrame
        return df[(df[date_column] >= past_date) & (df[date_column] <= run_dt)]



