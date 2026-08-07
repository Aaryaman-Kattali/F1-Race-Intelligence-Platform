"""
Lightweight model registry for versioning ML artifacts.

Stores model binaries (.pkl) alongside metadata JSON files in a
local directory structure:

    models/{model_name}/{timestamp}_{git_hash}.pkl
    models/{model_name}/{timestamp}_{git_hash}_metadata.json

Works with the existing XGBoost model (currently overwritten in-place).
"""

import json
import logging
import os
import pickle
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Lightweight, filesystem-based model registry.

    Usage::

        registry = ModelRegistry()
        registry.save_model(xgb_model, "xgboost_race_predictor", {
            "accuracy_top3": 0.72,
            "training_data": "2018-2024 race results",
            "features": ["form_score", "grid_position", ...],
        })

        model, meta = registry.load_latest("xgboost_race_predictor")
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.getenv("MODEL_REGISTRY_DIR", "models"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_git_hash(self) -> str:
        """Get current git short hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() or "nogit"
        except Exception:
            return "nogit"

    def _version_id(self) -> str:
        """Generate a version identifier: {timestamp}_{git_hash}."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        git_hash = self._get_git_hash()
        return f"{ts}_{git_hash}"

    def save_model(self, model: Any, name: str, metadata: Optional[Dict] = None) -> str:
        """
        Save a model artifact with metadata.

        Args:
            model: The model object (must be pickle-serialisable)
            name: Model name (e.g. "xgboost_race_predictor")
            metadata: Optional dict of training metadata

        Returns:
            Version ID string
        """
        model_dir = self.base_dir / name
        model_dir.mkdir(parents=True, exist_ok=True)

        version_id = self._version_id()
        model_path = model_dir / f"{version_id}.pkl"
        meta_path = model_dir / f"{version_id}_metadata.json"

        # Save model binary
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        # Build metadata
        meta = {
            "version_id": version_id,
            "model_name": name,
            "saved_at": datetime.utcnow().isoformat(),
            "git_hash": self._get_git_hash(),
            "model_path": str(model_path),
            "file_size_bytes": model_path.stat().st_size,
        }
        if metadata:
            meta.update(metadata)

        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2, default=str)

        logger.info(
            f"✅ Saved model '{name}' version {version_id} "
            f"({model_path.stat().st_size / 1024:.1f} KB)"
        )
        return version_id

    def list_versions(self, name: str) -> List[Dict]:
        """
        List all available versions of a model, sorted newest first.

        Returns:
            List of metadata dicts
        """
        model_dir = self.base_dir / name
        if not model_dir.exists():
            return []

        versions = []
        for meta_file in sorted(model_dir.glob("*_metadata.json"), reverse=True):
            try:
                with open(meta_file, "r") as f:
                    versions.append(json.load(f))
            except Exception as e:
                logger.warning(f"Skipping corrupt metadata {meta_file}: {e}")

        return versions

    def load_latest(self, name: str) -> tuple:
        """
        Load the most recent version of a model.

        Returns:
            (model_object, metadata_dict) or (None, None) if not found
        """
        versions = self.list_versions(name)
        if not versions:
            logger.warning(f"No versions found for model '{name}'")
            return None, None

        latest = versions[0]
        model_path = latest.get("model_path")

        if not model_path or not Path(model_path).exists():
            # Try reconstructing path
            model_dir = self.base_dir / name
            version_id = latest.get("version_id", "")
            model_path = model_dir / f"{version_id}.pkl"

        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            logger.info(f"✅ Loaded model '{name}' version {latest.get('version_id')}")
            return model, latest
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return None, None

    def load_version(self, name: str, version_id: str) -> tuple:
        """
        Load a specific version of a model.

        Returns:
            (model_object, metadata_dict) or (None, None)
        """
        model_dir = self.base_dir / name
        model_path = model_dir / f"{version_id}.pkl"
        meta_path = model_dir / f"{version_id}_metadata.json"

        if not model_path.exists():
            logger.error(f"Model version not found: {model_path}")
            return None, None

        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)

            metadata = {}
            if meta_path.exists():
                with open(meta_path, "r") as f:
                    metadata = json.load(f)

            return model, metadata
        except Exception as e:
            logger.error(f"❌ Failed to load version {version_id}: {e}")
            return None, None

    def delete_version(self, name: str, version_id: str) -> bool:
        """Delete a specific model version."""
        model_dir = self.base_dir / name
        model_path = model_dir / f"{version_id}.pkl"
        meta_path = model_dir / f"{version_id}_metadata.json"

        deleted = False
        for path in [model_path, meta_path]:
            if path.exists():
                path.unlink()
                deleted = True

        if deleted:
            logger.info(f"🗑️ Deleted model '{name}' version {version_id}")
        return deleted

    def get_summary(self, name: str) -> Dict:
        """Get a summary of a model's version history."""
        versions = self.list_versions(name)
        if not versions:
            return {"model_name": name, "total_versions": 0}

        return {
            "model_name": name,
            "total_versions": len(versions),
            "latest_version": versions[0].get("version_id"),
            "latest_saved_at": versions[0].get("saved_at"),
            "oldest_version": versions[-1].get("version_id"),
            "total_size_mb": round(
                sum(v.get("file_size_bytes", 0) for v in versions) / (1024 * 1024), 2
            ),
        }
