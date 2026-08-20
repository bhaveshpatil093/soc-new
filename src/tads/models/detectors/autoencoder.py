"""
Unsupervised PyTorch Autoencoder anomaly detector.

Trains exclusively on July data using a chronological train/validation split.
Anomaly score = per-window mean squared reconstruction error (MSE).

The raw reconstruction error is NOT a probability. It measures how poorly
the autoencoder (trained on normal July patterns) can reconstruct a given
window's feature vector. Higher error = more anomalous.

Calibration uses the same empirical-quantile approach as the Isolation Forest
(Prompt 43) for consistency across detectors.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa
import torch
from torch import nn

from tads.models.calibration import EmpiricalCalibrator
from tads.models.detectors.base import BaseAnomalyDetector

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class _AutoencoderNetwork(nn.Module):
    """
    Symmetric feedforward autoencoder.

    Architecture: input_dim → hidden_dim → latent_dim → hidden_dim → input_dim

    This is intentionally simple. The goal is a learnable baseline that captures
    the multivariate correlation structure of normal July windows, not a
    state-of-the-art generative model.
    """

    def __init__(self, input_dim: int, hidden_dim: int, latent_dim: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


class AutoencoderDetector(BaseAnomalyDetector):  # type: ignore[misc]
    """
    Unsupervised autoencoder anomaly detector.

    Trains on July data, scores windows by reconstruction error (MSE).
    Higher reconstruction error = more anomalous.

    Configuration (architecture, learning rate, epochs, seed) is persisted
    together with the model weights and preprocessing as one versioned artifact.
    """

    def __init__(
        self,
        feature_columns: list[str],
        hidden_dim: int = 32,
        latent_dim: int = 8,
        learning_rate: float = 1e-3,
        epochs: int = 50,
        batch_size: int = 256,
        val_split_frac: float = 0.2,
        seed: int = 42,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.feature_columns = feature_columns
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.val_split_frac = val_split_frac
        self.seed = seed

        # Will be set during fit
        self._network: _AutoencoderNetwork | None = None
        self._feature_means: np.ndarray | None = None
        self._feature_stds: np.ndarray | None = None
        self.training_history: list[dict[str, float]] = []
        self.calibrator: EmpiricalCalibrator | None = None

    def _extract_features(self, data: pa.Table) -> np.ndarray:
        """Extract feature columns into a numpy array."""
        missing = [f for f in self.feature_columns if f not in data.column_names]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        arrays = []
        for col in self.feature_columns:
            arrays.append(data.column(col).to_numpy().astype(np.float32))
        return np.column_stack(arrays)

    def _standardize(self, x: np.ndarray, fit: bool = False) -> np.ndarray:
        """
        Standardize features using July-fitted mean/std.

        This is NOT min-max normalization. It is a z-score standardization
        using robust statistics computed once from July training data.
        """
        if fit:
            self._feature_means = np.mean(x, axis=0)
            self._feature_stds = np.std(x, axis=0)
            # Prevent division by zero for constant features
            self._feature_stds[self._feature_stds < 1e-8] = 1.0

        if self._feature_means is None or self._feature_stds is None:
            raise ValueError("Standardization parameters not fitted.")

        return (x - self._feature_means) / self._feature_stds

    def _fit(self, data: pa.Table) -> None:
        """
        Train the autoencoder on July data with a chronological validation split.

        The split is strictly chronological: the first (1 - val_split_frac) fraction
        of windows (by their order in the table, which should be time-sorted) is used
        for training, and the last val_split_frac fraction is used for validation.
        This prevents temporal leakage even within July.
        """
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)

        raw_features = self._extract_features(data)
        n_samples = len(raw_features)
        input_dim = raw_features.shape[1]

        # Chronological split — NO shuffling
        split_idx = int(n_samples * (1 - self.val_split_frac))
        train_raw = raw_features[:split_idx]
        val_raw = raw_features[split_idx:]

        # Fit standardization on training split only
        train_std = self._standardize(train_raw, fit=True)
        val_std = self._standardize(val_raw, fit=False)

        train_tensor = torch.tensor(train_std, dtype=torch.float32)
        val_tensor = torch.tensor(val_std, dtype=torch.float32)

        # Build network
        self._network = _AutoencoderNetwork(input_dim, self.hidden_dim, self.latent_dim)
        optimizer = torch.optim.Adam(self._network.parameters(), lr=self.learning_rate)
        criterion = nn.MSELoss()

        # Training loop
        self.training_history = []
        train_dataset = torch.utils.data.TensorDataset(train_tensor)
        train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=self.batch_size, shuffle=True
        )

        for epoch in range(self.epochs):
            # Training
            self._network.train()
            epoch_train_loss = 0.0
            n_batches = 0
            for (batch,) in train_loader:
                optimizer.zero_grad()
                reconstructed = self._network(batch)
                loss = criterion(reconstructed, batch)
                loss.backward()
                optimizer.step()
                epoch_train_loss += loss.item()
                n_batches += 1
            avg_train_loss = epoch_train_loss / max(n_batches, 1)

            # Validation
            self._network.eval()
            with torch.no_grad():
                val_reconstructed = self._network(val_tensor)
                val_loss = criterion(val_reconstructed, val_tensor).item()

            self.training_history.append({
                "epoch": epoch + 1,
                "train_loss": avg_train_loss,
                "val_loss": val_loss,
            })

        logger.info(
            "Autoencoder training complete. Final train_loss=%.6f, val_loss=%.6f",
            self.training_history[-1]["train_loss"],
            self.training_history[-1]["val_loss"],
        )

    def score(self, data: pa.Table) -> pa.Array:
        """
        Score windows by per-sample mean squared reconstruction error.

        CRITICAL: The raw score is a reconstruction error magnitude,
        NOT a probability. Higher error = more anomalous.
        """
        if self._network is None:
            raise ValueError("Network not fitted.")

        raw_features = self._extract_features(data)
        std_features = self._standardize(raw_features, fit=False)
        input_tensor = torch.tensor(std_features, dtype=torch.float32)

        self._network.eval()
        with torch.no_grad():
            reconstructed = self._network(input_tensor)
            # Per-sample MSE (mean across features for each window)
            mse_per_sample = torch.mean((input_tensor - reconstructed) ** 2, dim=1)

        return pa.array(mse_per_sample.numpy().tolist())

    def fit_calibrator(
        self, data: pa.Table, threshold_evidence: float = 0.95
    ) -> None:
        """Fit the empirical calibrator on July training scores."""
        raw_scores = self.score(data)
        self.calibrator = EmpiricalCalibrator(
            model_version=self.version, threshold_evidence=threshold_evidence
        )
        self.calibrator.fit(raw_scores, data=data)
        self.threshold = threshold_evidence

    def _calibrate(self, raw_scores: pa.Array) -> pa.Array:
        """Map raw reconstruction errors to calibrated evidence via July CDF."""
        if self.calibrator is not None and self.calibrator.is_fitted:
            return self.calibrator.calibrate(raw_scores)
        return raw_scores

    def explain(self, data: pa.Table) -> pa.Array:
        """
        Per-feature reconstruction error breakdown.
        Shows which features contributed most to the anomaly score.
        """
        if self._network is None:
            raise ValueError("Network not fitted.")

        raw_features = self._extract_features(data)
        std_features = self._standardize(raw_features, fit=False)
        input_tensor = torch.tensor(std_features, dtype=torch.float32)

        self._network.eval()
        with torch.no_grad():
            reconstructed = self._network(input_tensor)
            per_feature_error = (input_tensor - reconstructed) ** 2

        explanations = []
        for i in range(len(data)):
            errors = per_feature_error[i].numpy()
            parts = [
                f"{self.feature_columns[j]}={errors[j]:.4f}"
                for j in range(len(self.feature_columns))
            ]
            explanations.append("recon_error: " + ", ".join(parts))

        return pa.array(explanations)

    def save(self, path: Path) -> None:
        """
        Persist model weights, preprocessing, configuration, and calibration
        as one versioned artifact.
        """
        if not self.is_fitted or self._network is None:
            raise ValueError("Cannot save an unfitted detector.")

        state = {
            # Versioning
            "version": self.version,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            # Configuration (architecture, hyperparameters)
            "feature_columns": self.feature_columns,
            "hidden_dim": self.hidden_dim,
            "latent_dim": self.latent_dim,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "seed": self.seed,
            # Preprocessing
            "feature_means": self._feature_means.tolist() if self._feature_means is not None else None,
            "feature_stds": self._feature_stds.tolist() if self._feature_stds is not None else None,
            # Model weights
            "model_state_dict": {
                k: v.cpu().numpy().tolist() for k, v in self._network.state_dict().items()
            },
            # Training history
            "training_history": self.training_history,
            # Calibrator
            "calibrator_sorted_scores": (
                self.calibrator._sorted_scores.tolist()
                if self.calibrator is not None and self.calibrator._sorted_scores is not None
                else None
            ),
            "calibrator_threshold": (
                self.calibrator.threshold_evidence
                if self.calibrator is not None
                else None
            ),
        }

        path.write_text(json.dumps(state))

    def load(self, path: Path) -> None:
        """Load the coupled model artifact."""
        if not path.exists():
            raise FileNotFoundError(f"Missing model artifact: {path}")

        state = json.loads(path.read_text())

        self.version = state["version"]
        self.threshold = state["threshold"]
        self.is_fitted = state["is_fitted"]
        self.feature_columns = state["feature_columns"]
        self.hidden_dim = state["hidden_dim"]
        self.latent_dim = state["latent_dim"]
        self.learning_rate = state["learning_rate"]
        self.epochs = state["epochs"]
        self.batch_size = state["batch_size"]
        self.seed = state["seed"]

        if state["feature_means"] is not None:
            self._feature_means = np.array(state["feature_means"], dtype=np.float32)
        if state["feature_stds"] is not None:
            self._feature_stds = np.array(state["feature_stds"], dtype=np.float32)

        # Rebuild network and load weights
        input_dim = len(self.feature_columns)
        self._network = _AutoencoderNetwork(input_dim, self.hidden_dim, self.latent_dim)
        sd = {
            k: torch.tensor(v)
            for k, v in state["model_state_dict"].items()
        }
        self._network.load_state_dict(sd)
        self._network.eval()

        self.training_history = state.get("training_history", [])

        # Restore calibrator
        cal_scores = state.get("calibrator_sorted_scores")
        cal_threshold = state.get("calibrator_threshold")
        if cal_scores is not None and cal_threshold is not None:
            self.calibrator = EmpiricalCalibrator(
                model_version=self.version, threshold_evidence=cal_threshold
            )
            self.calibrator._sorted_scores = np.array(cal_scores)
            self.calibrator._n_scores = len(cal_scores)
            self.calibrator.is_fitted = True
