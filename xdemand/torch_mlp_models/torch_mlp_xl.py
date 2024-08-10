import logging
from typing import Union

import torch
from torch import nn
from torch.nn.modules import loss as ls

from ctr_predictor.models.self_attention import SelfAttention
from ctr_predictor.models.torch_base_model import TorchBaseModel

# Set up the logger context
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set the logging level

# Type hint for loss functions
LossTypes = [getattr(ls, name) for name in ls.__all__]
LossType = Union[tuple(LossTypes)]


class MLP_XL(TorchBaseModel):
    def __init__(self, input_size, hidden_layer_sizes, activation="relu", dropout_rate=0.1,
                 use_attention=False, output_activation='none', config=None):
        super(MLP_XL, self).__init__()
        self.use_attention = use_attention
        layers = []

        # Check the activation function for the middle layers
        activation_fn = self.get_activation_function(activation)

        if hidden_layer_sizes is None:
            layers = [nn.Linear(input_size, 1)]
        else:
            # Dynamically adding hidden layers
            previous_size = input_size
            for size in hidden_layer_sizes:
                layers.append(nn.Linear(previous_size, size))
                layers.append(activation_fn)
                layers.append(nn.Dropout(dropout_rate))

                # Use the new norm_batch structure from config
                if config['norm_batch']['use_norm_batch']:
                    bn_params = config['norm_batch']['parameters']
                    layers.append(nn.BatchNorm1d(size, **bn_params))

                previous_size = size

            # Optional: Add self-attention to the last hidden layer's output
            if use_attention:
                self.attention = SelfAttention(hidden_layer_sizes[-1])
                layers.append(self.attention)

            # Add the output layer
            layers.append(nn.Linear(hidden_layer_sizes[-1], 1))

        # Determine the output activation function and append as a layer
        output_activation_fn = self.get_activation_function(output_activation)
        layers.append(output_activation_fn)

        # Combine all layers into a single sequential module
        self.layers = nn.Sequential(*layers)
        logger.info('MLP_XL model specs: %s', layers)

    def forward(self, x):
        return self.layers(x)

    @staticmethod
    def get_activation_function(activation):
        if activation == 'relu':
            return nn.ReLU()
        elif activation == 'sigmoid':
            return nn.Sigmoid()
        elif activation == "leaky_relu":
            return nn.LeakyReLU()
        elif activation == 'tanh':
            return nn.Tanh()
        else:
            return nn.Identity()