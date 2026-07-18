"""
CNN Model for Captcha Character Recognition
============================================
Self-contained CNN architecture that can be trained on custom captcha datasets.
Uses only PyTorch (no external captcha-specific libraries needed).

Architecture:
- Input: single character image (grayscale, 28x28 or 32x32)
- 3 Conv blocks with BatchNorm + ReLU + MaxPool
- 2 Fully connected layers
- Output: character class (digits + uppercase letters = 36 classes)

Usage:
    # Training:
    model = CaptchaCNN(num_classes=36, img_size=32)
    model.train_on_dataset("./data/chars/")

    # Inference:
    model.load("./models/captcha_cnn.pth")
    prediction = model.predict(char_image)
"""

import os
import io
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger("captcha-solver.models.cnn")

# Character set: digits + uppercase letters
DEFAULT_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class CaptchaCNNNet(nn.Module):
    """CNN architecture for single character recognition."""

    def __init__(self, num_classes: int = 36, img_size: int = 32):
        super().__init__()
        self.img_size = img_size

        # Conv Block 1: 1 → 32 channels
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.25),
        )

        # Conv Block 2: 32 → 64 channels
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.25),
        )

        # Conv Block 3: 64 → 128 channels
        self.conv3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.25),
        )

        # Calculate FC input size
        fc_size = img_size // 8  # 3 MaxPool2d(2,2) layers
        fc_input = 128 * fc_size * fc_size

        # Fully connected
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(fc_input, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.fc(x)
        return x


class CaptchaCNN:
    """
    High-level wrapper for training and inference with the captcha CNN.

    Handles:
    - Model loading/saving
    - Image preprocessing for inference
    - Training from a folder of character images
    - Multi-character captcha decoding (with segmentation)
    """

    def __init__(
        self,
        num_classes: int = 36,
        img_size: int = 32,
        charset: str = DEFAULT_CHARSET,
        model_path: Optional[str] = None,
    ):
        if not HAS_TORCH:
            raise ImportError("PyTorch is required: pip install torch torchvision")

        self.num_classes = num_classes
        self.img_size = img_size
        self.charset = charset
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Initialize model
        self.model = CaptchaCNNNet(num_classes=num_classes, img_size=img_size)
        self.model.to(self.device)

        # Load weights if provided
        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def load(self, path: str):
        """Load model weights from file."""
        state = torch.load(path, map_location=self.device)
        if "model_state" in state:
            self.model.load_state_dict(state["model_state"])
            self.charset = state.get("charset", self.charset)
            self.img_size = state.get("img_size", self.img_size)
        else:
            self.model.load_state_dict(state)
        self.model.eval()
        logger.info(f"Model loaded from {path}")

    def save(self, path: str):
        """Save model weights and metadata."""
        state = {
            "model_state": self.model.state_dict(),
            "charset": self.charset,
            "img_size": self.img_size,
            "num_classes": self.num_classes,
        }
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        torch.save(state, path)
        logger.info(f"Model saved to {path}")

    def predict_char(self, img: "Image.Image") -> Tuple[str, float]:
        """
        Predict a single character from an image.

        Args:
            img: PIL Image of a single character

        Returns:
            (character, confidence) tuple
        """
        self.model.eval()
        tensor = self._image_to_tensor(img)

        with torch.no_grad():
            output = self.model(tensor)
            probs = torch.softmax(output, dim=1)
            confidence, predicted = torch.max(probs, 1)

            char_idx = predicted.item()
            conf = confidence.item()

            if char_idx < len(self.charset):
                return self.charset[char_idx], conf
            return "?", 0.0

    def predict_captcha(
        self,
        img: "Image.Image",
        num_chars: int = 0
    ) -> Tuple[str, float]:
        """
        Predict an entire captcha image (multi-character).
        Segments the image into characters and predicts each.

        Args:
            img: Full captcha image
            num_chars: Expected number of characters (0 = auto)

        Returns:
            (full_text, average_confidence) tuple
        """
        from ..preprocessing import ImageProcessor

        # Preprocess
        processed = ImageProcessor.full_pipeline(img, scale_factor=1.0)

        # Segment characters
        char_images = ImageProcessor.segment_characters(processed, num_chars)

        if not char_images:
            return "", 0.0

        # Predict each character
        text = ""
        total_conf = 0.0

        for char_img in char_images:
            char, conf = self.predict_char(char_img)
            text += char
            total_conf += conf

        avg_conf = total_conf / len(char_images) if char_images else 0.0
        return text, avg_conf

    def _image_to_tensor(self, img: "Image.Image") -> "torch.Tensor":
        """Convert PIL Image to model input tensor."""
        # Ensure grayscale
        if img.mode != "L":
            img = img.convert("L")

        # Resize to model's expected size
        img = img.resize((self.img_size, self.img_size), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)

        # Convert to tensor [0, 1]
        import numpy as np
        arr = np.array(img, dtype=np.float32) / 255.0

        # Invert if white text on black (model expects black text on white)
        if arr.mean() < 0.5:
            arr = 1.0 - arr

        # Shape: [1, 1, H, W]
        tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0)
        return tensor.to(self.device)

    def train_on_dataset(
        self,
        data_dir: str,
        epochs: int = 20,
        batch_size: int = 64,
        learning_rate: float = 0.001,
        save_path: Optional[str] = None,
    ) -> dict:
        """
        Train the model on a folder of character images.

        Expected folder structure:
            data_dir/
                0/   ← images of character '0'
                    img001.png
                    img002.png
                1/   ← images of character '1'
                    ...
                A/   ← images of character 'A'
                    ...

        Or alternatively, filenames encode the label:
            data_dir/
                0_001.png
                0_002.png
                A_001.png
                ...

        Args:
            data_dir: Path to training data
            epochs: Number of training epochs
            batch_size: Batch size
            learning_rate: Learning rate
            save_path: Where to save the trained model

        Returns:
            Training stats dict
        """
        dataset = CaptchaCharDataset(data_dir, self.charset, self.img_size)

        if len(dataset) == 0:
            return {"error": "No training data found"}

        # Split train/val (90/10)
        train_size = int(0.9 * len(dataset))
        val_size = len(dataset) - train_size
        train_ds, val_ds = torch.utils.data.random_split(dataset, [train_size, val_size])

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.5)

        self.model.train()
        history = {"train_loss": [], "val_acc": []}

        for epoch in range(epochs):
            total_loss = 0
            for images, labels in train_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                optimizer.zero_grad()
                outputs = self.model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            scheduler.step()
            avg_loss = total_loss / len(train_loader)
            history["train_loss"].append(avg_loss)

            # Validation
            val_acc = self._validate(val_loader)
            history["val_acc"].append(val_acc)

            logger.info(
                f"Epoch {epoch+1}/{epochs} - "
                f"Loss: {avg_loss:.4f} - Val Acc: {val_acc:.2%}"
            )

        # Save model
        if save_path:
            self.save(save_path)

        return {
            "epochs": epochs,
            "samples": len(dataset),
            "final_loss": history["train_loss"][-1],
            "final_val_acc": history["val_acc"][-1],
        }

    def _validate(self, val_loader) -> float:
        """Run validation and return accuracy."""
        self.model.eval()
        correct = 0
        total = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                outputs = self.model(images)
                _, predicted = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        self.model.train()
        return correct / total if total > 0 else 0.0


class CaptchaCharDataset(Dataset):
    """Dataset for individual character images."""

    def __init__(self, root_dir: str, charset: str, img_size: int):
        self.img_size = img_size
        self.charset = charset
        self.samples: List[Tuple[str, int]] = []  # (path, label_idx)

        if not os.path.exists(root_dir):
            logger.warning(f"Data directory not found: {root_dir}")
            return

        # Check if organized in subdirectories
        subdirs = [d for d in os.listdir(root_dir)
                   if os.path.isdir(os.path.join(root_dir, d))]

        if subdirs:
            # Folder structure: root/A/, root/B/, etc.
            for char_dir in subdirs:
                char = char_dir.upper() if len(char_dir) == 1 else char_dir
                if char in charset:
                    label_idx = charset.index(char)
                    dir_path = os.path.join(root_dir, char_dir)
                    for fname in os.listdir(dir_path):
                        if fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                            self.samples.append(
                                (os.path.join(dir_path, fname), label_idx)
                            )
        else:
            # Flat structure: root/A_001.png, root/0_002.png
            for fname in os.listdir(root_dir):
                if fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    # First character of filename is the label
                    char = fname[0].upper()
                    if char in charset:
                        label_idx = charset.index(char)
                        self.samples.append(
                            (os.path.join(root_dir, fname), label_idx)
                        )

        logger.info(f"Loaded {len(self.samples)} samples from {root_dir}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        import numpy as np

        path, label = self.samples[idx]
        img = Image.open(path).convert("L")
        img = img.resize((self.img_size, self.img_size),
                         Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)

        arr = np.array(img, dtype=np.float32) / 255.0

        # Ensure black text on white bg
        if arr.mean() < 0.5:
            arr = 1.0 - arr

        tensor = torch.from_numpy(arr).unsqueeze(0)  # [1, H, W]
        return tensor, label
