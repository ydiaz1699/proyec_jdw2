"""
CNN Model for Captcha Recognition
==================================
Custom Convolutional Neural Network for recognizing text in captcha images.
Designed to predict multiple characters simultaneously.

Architecture:
- Input: Grayscale image (1 x H x W)
- 4 Conv blocks with BatchNorm and MaxPool
- Fully connected layers
- Output: (captcha_length x num_classes)

Requires:
- torch >= 2.0.0
"""

import torch
import torch.nn as nn


class CaptchaCNN(nn.Module):
    """
    CNN model for multi-character captcha recognition.
    Predicts all characters in the captcha simultaneously.
    """

    def __init__(
        self,
        num_classes: int = 36,
        captcha_length: int = 6,
        image_height: int = 60,
        image_width: int = 160,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.captcha_length = captcha_length
        self.image_height = image_height
        self.image_width = image_width

        # Convolutional feature extractor
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            # Block 2
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            # Block 3
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            # Block 4
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.25),
        )

        # Calculate flattened feature size
        feat_h = image_height // 16  # 4 MaxPool layers
        feat_w = image_width // 16
        self._flat_size = 256 * feat_h * feat_w

        # Classifier: one head per character position
        self.classifier = nn.Sequential(
            nn.Linear(self._flat_size, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
        )

        # Separate output heads for each character position
        self.char_heads = nn.ModuleList([
            nn.Linear(512, num_classes)
            for _ in range(captcha_length)
        ])


    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (batch, 1, H, W)

        Returns:
            Tensor of shape (batch, captcha_length, num_classes)
        """
        # Extract features
        x = self.features(x)

        # Flatten
        x = x.view(x.size(0), -1)

        # Shared classifier
        x = self.classifier(x)

        # Per-character predictions
        outputs = [head(x) for head in self.char_heads]

        # Stack: (batch, captcha_length, num_classes)
        return torch.stack(outputs, dim=1)


class CaptchaLoss(nn.Module):
    """
    Multi-character cross-entropy loss for captcha recognition.
    Applies CrossEntropy independently to each character position.
    """

    def __init__(self):
        super().__init__()
        self.criterion = nn.CrossEntropyLoss()

    def forward(
        self, predictions: torch.Tensor, targets: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute loss.

        Args:
            predictions: (batch, captcha_length, num_classes)
            targets: (batch, captcha_length) - class indices

        Returns:
            Scalar loss tensor.
        """
        batch_size, captcha_length, _ = predictions.shape
        total_loss = 0.0

        for i in range(captcha_length):
            char_pred = predictions[:, i, :]
            char_target = targets[:, i]
            total_loss += self.criterion(char_pred, char_target)

        return total_loss / captcha_length
