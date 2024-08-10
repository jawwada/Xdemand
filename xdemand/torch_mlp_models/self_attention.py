import torch
import torch.nn.functional as F
from torch import nn


class SelfAttention(nn.Module):
    """
    Self-attention mechanism for neural networks.
    """

    def __init__(self, feature_dim):
        super(SelfAttention, self).__init__()
        self.scale = 1.0 / (feature_dim ** 0.5)

    def forward(self, x):
        """
        Forward pass of the self-attention mechanism.
        Args:
            x: The input tensor.
        Returns: attended

        """
        # Assuming x is of shape [batch, features], add a sequence dimension
        x = x.unsqueeze(1)
        # Batch matrix multiplication
        scores = torch.bmm(x, x.transpose(1, 2)) * self.scale
        weights = F.softmax(scores, dim=-1)
        attended = torch.bmm(weights, x).squeeze(1)
        return attended
