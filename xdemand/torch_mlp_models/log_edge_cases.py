import os
import torch
import mlflow
import argparse
import logging
from ctr_predictor.logging.mlflow import MLflowLogger

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_model_edge_cases(model, input_size, mlflow_logger: MLflowLogger, previous_week_rate: float= 0.00065):
    model.eval()
    # Prepare the tensors for edge cases
    input_tensor1 = torch.ones(1, input_size)*0.02
    input_tensor1[0, 0] = previous_week_rate

    input_tensor2 = torch.zeros(1, input_size)
    input_tensor2[0, 0] = previous_week_rate

    input_tensor3 = torch.ones(1, input_size)
    input_tensor3[0, 0] = previous_week_rate

    # Perform inference
    with torch.no_grad():
        prediction1 = model(input_tensor1)
        prediction2 = model(input_tensor2)
        prediction3 = model(input_tensor3)


    edge_case1 = prediction1.item()
    edge_case2 = prediction2.item()

    # Log results to MLflow

    mlflow_logger.log_metric("edge_case1_LT0.2", edge_case1)
    mlflow_logger.log_metric("edge_case2_LTs0", edge_case2)


    logger.info(f"Prediction edge case 1 (whole row LTS missing - mean): {edge_case1}")
    logger.info(f"Prediction edge case 2 (whole row LTS  missing 0): {edge_case2}")
    return
