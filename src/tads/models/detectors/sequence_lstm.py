"""
Sequence-based unsupervised anomaly detector using a causal LSTM.

Architecture: Next-Window Prediction
  - Input: a sequence of K consecutive 5-second feature windows
  - At each timestep t, the LSTM encodes windows [0..t] and predicts
    window t+1's features
  - Anomaly score = MSE between predicted and actual next window

This is a CAUSAL model: the LSTM processes the sequence left-to-right,
and the prediction for timestep t uses ONLY windows at positions <= t.
No future information leakage occurs by construction (no bidirectional
layers, no attention over future positions, no teacher forcing with
future ground truth).

The raw prediction error is NOT a probability. It measures how surprising
the next window is given the preceding sequence. Higher error = the
temporal transition is more anomalous relative to July's learned patterns.
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


class _CausalLSTMPredictor(nn.Module):
    """
    Causal LSTM for next-window prediction.

    At each timestep t in a sequence of length T, this model:
      1. Encodes windows [0..t] via the LSTM hidden state
      2. Projects the hidden state to predict window t+1's features

    No future leakage: the LSTM is unidirectional (left-to-right only),
    and the prediction head at position t sees only the hidden state
    accumulated from positions [0..t].
    """

    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int = 1) -> None:
        super().__init__()
        # Unidirectional LSTM — strictly causal
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=False,  # CRITICAL: no future access
        )
        # Prediction head: map hidden state to next-window features
        self.predictor = nn.Linear(hidden_dim, input_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, input_dim)

        Returns:
            predictions: (batch, seq_len, input_dim)
                predictions[:, t, :] = predicted features for window t+1,
                using only windows [0..t] as context.
        """
        # lstm_out: (batch, seq_len, hidden_dim)
        # Each lstm_out[:, t, :] encodes only x[:, 0:t+1, :]
        lstm_out, _ = self.lstm(x)
        predictions = self.predictor(lstm_out)
        return predictions


class SequenceLSTMDetector(BaseAnomalyDetector):  # type: ignore[misc]
    """
    Sequence-based anomaly detector using causal LSTM next-window prediction.

    Trains on July sequences of consecutive 5-second windows.
    Scores each window by how poorly the model predicted it from
    the preceding context.

    The raw score is a prediction error (MSE), NOT a probability.
    """

    def __init__(
        self,
        feature_columns: list[str],
        seq_len: int = 12,
        hidden_dim: int = 32,
        num_layers: int = 1,
        learning_rate: float = 1e-3,
        epochs: int = 30,
        batch_size: int = 64,
        val_split_frac: float = 0.2,
        seed: int = 42,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.feature_columns = feature_columns
        self.seq_len = seq_len
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.val_split_frac = val_split_frac
        self.seed = seed

        self._network: _CausalLSTMPredictor | None = None
        self._feature_means: np.ndarray | None = None
        self._feature_stds: np.ndarray | None = None
        self.training_history: list[dict[str, float]] = []
        self.calibrator: EmpiricalCalibrator | None = None

    def _extract_features(self, data: pa.Table) -> np.ndarray:
        """Extract feature columns into (n_windows, n_features) array."""
        missing = [f for f in self.feature_columns if f not in data.column_names]
        if missing:
            raise ValueError(f"Missing required features: {missing}")
        arrays = [data.column(col).to_numpy().astype(np.float32) for col in self.feature_columns]
        return np.column_stack(arrays)

    def _standardize(self, x: np.ndarray, *, fit: bool = False) -> np.ndarray:
        """Z-score standardization using July-fitted parameters. NOT min-max."""
        if fit:
            self._feature_means = np.mean(x, axis=0)
            self._feature_stds = np.std(x, axis=0)
            self._feature_stds[self._feature_stds < 1e-8] = 1.0
        if self._feature_means is None or self._feature_stds is None:
            raise ValueError("Standardization parameters not fitted.")
        return (x - self._feature_means) / self._feature_stds

    def _make_sequences(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Create overlapping sequences for next-window prediction.

        For a sequence of length K+1 starting at index i:
          input  = features[i : i+K]      (the context)
          target = features[i+1 : i+K+1]  (the next windows to predict)

        This means: given windows [i..i+K-1], predict [i+1..i+K].
        At position t within the input, the target is the actual window at t+1.
        """
        n = len(features)
        inputs = []
        targets = []
        for i in range(n - self.seq_len):
            inputs.append(features[i : i + self.seq_len])
            targets.append(features[i + 1 : i + self.seq_len + 1])
        return np.array(inputs), np.array(targets)

    def _fit(self, data: pa.Table) -> None:
        """Train with chronological split. No shuffling of sequences."""
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)

        raw = self._extract_features(data)
        n_total = len(raw)

        # Chronological split
        split_idx = int(n_total * (1 - self.val_split_frac))
        train_raw = raw[:split_idx]
        val_raw = raw[split_idx:]

        # Fit standardization on training only
        train_std = self._standardize(train_raw, fit=True)
        val_std = self._standardize(val_raw, fit=False)

        # Create sequences
        train_inputs, train_targets = self._make_sequences(train_std)
        val_inputs, val_targets = self._make_sequences(val_std)

        train_x = torch.tensor(train_inputs, dtype=torch.float32)
        train_y = torch.tensor(train_targets, dtype=torch.float32)
        val_x = torch.tensor(val_inputs, dtype=torch.float32)
        val_y = torch.tensor(val_targets, dtype=torch.float32)

        input_dim = train_x.shape[2]
        self._network = _CausalLSTMPredictor(input_dim, self.hidden_dim, self.num_layers)
        optimizer = torch.optim.Adam(self._network.parameters(), lr=self.learning_rate)
        criterion = nn.MSELoss()

        dataset = torch.utils.data.TensorDataset(train_x, train_y)
        # shuffle=True is OK here: we shuffle *sequences* not individual windows.
        # Each sequence is internally time-ordered, and the LSTM is causal within it.
        loader = torch.utils.data.DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        self.training_history = []
        for epoch in range(self.epochs):
            self._network.train()
            epoch_loss = 0.0
            n_batches = 0
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                preds = self._network(batch_x)
                loss = criterion(preds, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
                n_batches += 1

            self._network.eval()
            with torch.no_grad():
                val_preds = self._network(val_x)
                val_loss = criterion(val_preds, val_y).item()

            self.training_history.append({
                "epoch": epoch + 1,
                "train_loss": epoch_loss / max(n_batches, 1),
                "val_loss": val_loss,
            })

        logger.info(
            "LSTM training complete. Final train=%.6f, val=%.6f",
            self.training_history[-1]["train_loss"],
            self.training_history[-1]["val_loss"],
        )

    def score(self, data: pa.Table) -> pa.Array:
        """
        Score each window by its prediction error.

        For windows that don't have enough preceding context (the first
        seq_len-1 windows), we use a shorter context. The score for
        window t is the MSE between the model's prediction (given all
        preceding windows) and the actual window t.

        CRITICAL: The raw score is a prediction error, NOT a probability.
        """
        if self._network is None:
            raise ValueError("Network not fitted.")

        raw = self._extract_features(data)
        std = self._standardize(raw, fit=False)
        n = len(std)
        std.shape[1]

        self._network.eval()
        scores = np.zeros(n, dtype=np.float32)

        # For the first window, there's no prediction possible — score is 0
        # For subsequent windows, we use the maximum available context up to seq_len
        with torch.no_grad():
            for t in range(1, n):
                ctx_start = max(0, t - self.seq_len)
                context = std[ctx_start:t]  # windows before t
                context_tensor = torch.tensor(context, dtype=torch.float32).unsqueeze(0)
                preds = self._network(context_tensor)  # (1, ctx_len, input_dim)
                # The last prediction corresponds to predicting window t
                predicted = preds[0, -1, :].numpy()
                actual = std[t]
                scores[t] = float(np.mean((predicted - actual) ** 2))

        return pa.array(scores.tolist())

    def score_batched(self, data: pa.Table) -> pa.Array:
        """
        Efficient batched scoring using full sequences.
        Returns per-window scores for all windows that have full context.
        Windows with insufficient context get score=0.
        """
        if self._network is None:
            raise ValueError("Network not fitted.")

        raw = self._extract_features(data)
        std = self._standardize(raw, fit=False)
        n = len(std)

        self._network.eval()
        scores = np.zeros(n, dtype=np.float32)

        if n <= self.seq_len:
            return pa.array(scores.tolist())

        # Build all full-length sequences
        inputs, targets = self._make_sequences(std)
        x_tensor = torch.tensor(inputs, dtype=torch.float32)
        y_tensor = torch.tensor(targets, dtype=torch.float32)

        with torch.no_grad():
            preds = self._network(x_tensor)
            # Per-sequence, per-timestep MSE
            per_step_mse = torch.mean((preds - y_tensor) ** 2, dim=2)  # (n_seq, seq_len)

        # Map back: sequence i, position j → window (i + j + 1)
        # For overlapping sequences, we average the scores
        counts = np.zeros(n, dtype=np.float32)
        mse_np = per_step_mse.numpy()
        for i in range(len(mse_np)):
            for j in range(self.seq_len):
                window_idx = i + j + 1
                scores[window_idx] += mse_np[i, j]
                counts[window_idx] += 1

        mask = counts > 0
        scores[mask] /= counts[mask]

        return pa.array(scores.tolist())

    def fit_calibrator(self, data: pa.Table, threshold_evidence: float = 0.95) -> None:
        """Fit empirical calibrator on July scores."""
        raw_scores = self.score_batched(data)
        self.calibrator = EmpiricalCalibrator(
            model_version=self.version, threshold_evidence=threshold_evidence
        )
        self.calibrator.fit(raw_scores, data=data)
        self.threshold = threshold_evidence

    def _calibrate(self, raw_scores: pa.Array) -> pa.Array:
        if self.calibrator is not None and self.calibrator.is_fitted:
            return self.calibrator.calibrate(raw_scores)
        return raw_scores

    def explain(self, data: pa.Table) -> pa.Array:
        return pa.array(["Sequence prediction error"] * len(data))

    def save(self, path: Path) -> None:
        if not self.is_fitted or self._network is None:
            raise ValueError("Cannot save an unfitted detector.")
        state = {
            "version": self.version,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "feature_columns": self.feature_columns,
            "seq_len": self.seq_len,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "seed": self.seed,
            "feature_means": self._feature_means.tolist() if self._feature_means is not None else None,
            "feature_stds": self._feature_stds.tolist() if self._feature_stds is not None else None,
            "model_state_dict": {
                k: v.cpu().numpy().tolist() for k, v in self._network.state_dict().items()
            },
            "training_history": self.training_history,
            "calibrator_sorted_scores": (
                self.calibrator._sorted_scores.tolist()
                if self.calibrator is not None and self.calibrator._sorted_scores is not None
                else None
            ),
            "calibrator_threshold": (
                self.calibrator.threshold_evidence if self.calibrator is not None else None
            ),
        }
        path.write_text(json.dumps(state))

    def load(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Missing model artifact: {path}")
        state = json.loads(path.read_text())
        self.version = state["version"]
        self.threshold = state["threshold"]
        self.is_fitted = state["is_fitted"]
        self.feature_columns = state["feature_columns"]
        self.seq_len = state["seq_len"]
        self.hidden_dim = state["hidden_dim"]
        self.num_layers = state["num_layers"]
        self.learning_rate = state["learning_rate"]
        self.epochs = state["epochs"]
        self.batch_size = state["batch_size"]
        self.seed = state["seed"]
        if state["feature_means"] is not None:
            self._feature_means = np.array(state["feature_means"], dtype=np.float32)
        if state["feature_stds"] is not None:
            self._feature_stds = np.array(state["feature_stds"], dtype=np.float32)
        input_dim = len(self.feature_columns)
        self._network = _CausalLSTMPredictor(input_dim, self.hidden_dim, self.num_layers)
        sd = {k: torch.tensor(v) for k, v in state["model_state_dict"].items()}
        self._network.load_state_dict(sd)
        self._network.eval()
        self.training_history = state.get("training_history", [])
        cal_scores = state.get("calibrator_sorted_scores")
        cal_threshold = state.get("calibrator_threshold")
        if cal_scores is not None and cal_threshold is not None:
            self.calibrator = EmpiricalCalibrator(
                model_version=self.version, threshold_evidence=cal_threshold
            )
            self.calibrator._sorted_scores = np.array(cal_scores)
            self.calibrator._n_scores = len(cal_scores)
            self.calibrator.is_fitted = True
