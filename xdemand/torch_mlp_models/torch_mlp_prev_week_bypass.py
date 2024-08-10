import logging
from typing import Union

import torch
from torch import nn
from torch.nn.modules import loss as ls

from ctr_predictor.logging.logger import LoggerHandler
from ctr_predictor.models.self_attention import SelfAttention
from ctr_predictor.models.torch_base_model import TorchBaseModel


# Set up the logger context
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set the logging level

# Type hint for loss functions
# Create the list of types first
LossTypes = [getattr(ls, name) for name in ls.__all__]
# Then pass it to Union
LossType = Union[tuple(LossTypes)]

class MLP_XL(TorchBaseModel):
    """
    This class is an extended Multi-layer perceptron with support for dynamic hidden layers.
    Assuming the first variable is very close to the target, the model bypasses the first variable
    and processes the rest through hidden layers. The output of the last hidden layer is concatenated
    with the first variable and passed through the output layer.
    """
    def __init__(self, input_size, hidden_layer_sizes, activation="relu", dropout_rate=0.1, use_norm_batch=True, use_attention=False,
                 output_activation='none', config=None):
        super(MLP_XL, self).__init__()
        self.use_attention = use_attention
        self.input_size = input_size
        layers = []

        # Activation function for hidden layers
        if activation == 'relu':
            activation_fn = nn.ReLU()
        elif activation == 'sigmoid':
            activation_fn = nn.Sigmoid()
        elif activation == "leaky_relu":
            activation_fn = nn.LeakyReLU()
        elif activation == 'tanh':
            activation_fn = nn.Tanh()
        else:
            activation_fn = nn.Identity()

        # Dynamically adding hidden layers
        previous_size = input_size - 1  # Subtract 1 to account for the bypassed variable
        for size in hidden_layer_sizes:
            layers.append(nn.Linear(previous_size, size))
            layers.append(activation_fn)
            layers.append(nn.Dropout(dropout_rate))
            if use_norm_batch:
                layers.append(nn.BatchNorm1d(size))
            previous_size = size

        # Optional: Add self-attention to the last hidden layer's output
        if use_attention:
            self.attention = SelfAttention(hidden_layer_sizes[-1])
            layers.append(self.attention)

        # Combine all layers into a single sequential module
        self.hidden_layers = nn.Sequential(*layers)

        # Add the output layer
        self.output_layer = nn.Linear(hidden_layer_sizes[-1] + 1, 1)  # +1 for the bypassed variable

        # Determine the output activation function
        if output_activation == 'sigmoid':
            self.output_activation = nn.Sigmoid()
        elif output_activation == 'relu':
            self.output_activation = nn.ReLU()
        elif output_activation == 'tanh':
            self.output_activation = nn.Tanh()
        else:
            self.output_activation = nn.Identity()

        logger.info('MLP_XL model created with %d hidden layers', len(hidden_layer_sizes))
        logger.info('MLP_XL model specs: %s', self.hidden_layers)
        logger.info('MLP_XL output layer: %s', self.output_layer)

    def forward(self, x):
        # Split the input tensor
        first_var = x[:, 0].unsqueeze(1)  # Keep the first variable
        rest_vars = x[:, 1:]  # Process the rest through hidden layers

        # Process through hidden layers
        hidden_output = self.hidden_layers(rest_vars)

        # Concatenate the first variable with the output of hidden layers
        combined = torch.cat((first_var, hidden_output), dim=1)

        # Pass through the output layer
        output = self.output_layer(combined)

        # Apply output activation
        return self.output_activation(output)