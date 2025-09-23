"""
Tests for enhanced nested model validation support
"""
import pytest
from typing import Dict, List, Optional
from satya import Model, Field, ModelValidationError


class SystemConfig(Model):
    buffer_size: int = Field(ge=256, le=100000)
    learning_rate: float = Field(ge=0.0, le=1.0)
    max_epochs: int = Field(ge=1, le=1000)


class ArchiveEntry(Model):
    config: SystemConfig = Field(description="System configuration")
    performance: float = Field(ge=-1000.0, le=100000.0)
    generation: int = Field(ge=0)


class MapElitesArchive(Model):
    resolution: int = Field(ge=1, le=20)
    archive: Dict[str, ArchiveEntry] = Field(description="Archive entries")


class ExperimentResult(Model):
    model_params: SystemConfig
    accuracy: float = Field(ge=0.0, le=1.0)
    training_time: float = Field(ge=0.0)


class ExperimentSuite(Model):
    experiments: Dict[str, ExperimentResult] = Field(description="Experiment results")


def test_simple_dict_of_models():
    """Test basic Dict[str, Model] validation"""
    data = {
        "resolution": 5,
        "archive": {
            "cell_1_2": {
                "config": {
                    "buffer_size": 1024,
                    "learning_rate": 0.01,
                    "max_epochs": 100
                },
                "performance": 95.5,
                "generation": 10
            },
            "cell_2_3": {
                "config": {
                    "buffer_size": 2048,
                    "learning_rate": 0.001,
                    "max_epochs": 200
                },
                "performance": 97.2,
                "generation": 15
            }
        }
    }

    # Test regular validation
    archive = MapElitesArchive(**data)
    assert archive.resolution == 5
    assert len(archive.archive) == 2
    assert isinstance(archive.archive["cell_1_2"], ArchiveEntry)
    assert archive.archive["cell_1_2"].performance == 95.5
    assert archive.archive["cell_1_2"].config.buffer_size == 1024

def test_nested_dict_validation_errors():
    """Test that validation errors are properly propagated in nested dicts"""
    # Invalid buffer_size (too small)
    data = {
        "resolution": 5,
        "archive": {
            "cell_1_2": {
                "config": {
                    "buffer_size": 100,  # Too small (< 256)
                    "learning_rate": 0.01,
                    "max_epochs": 100
                },
                "performance": 95.5,
                "generation": 10
            }
        }
    }

    with pytest.raises(ModelValidationError) as exc_info:
        MapElitesArchive(**data)

    errors = exc_info.value.errors
    assert len(errors) > 0
    # Check that the error path includes the nested structure
    error_paths = [str(error) for error in errors]
    assert any("buffer_size" in path for path in error_paths)


def test_empty_dict_of_models():
    """Test Dict[str, Model] with empty dictionary"""
    data = {
        "resolution": 5,
        "archive": {}
    }

    archive = MapElitesArchive(**data)
    assert archive.resolution == 5
    assert len(archive.archive) == 0


def test_experiment_suite_validation():
    """Test more complex nested Dict[str, Model] structure"""
    data = {
        "experiments": {
            "exp_001": {
                "model_params": {
                    "buffer_size": 512,
                    "learning_rate": 0.1,
                    "max_epochs": 50
                },
                "accuracy": 0.85,
                "training_time": 120.5
            },
            "exp_002": {
                "model_params": {
                    "buffer_size": 1024,
                    "learning_rate": 0.01,
                    "max_epochs": 100
                },
                "accuracy": 0.92,
                "training_time": 240.0
            }
        }
    }

    suite = ExperimentSuite(**data)
    assert len(suite.experiments) == 2
    assert suite.experiments["exp_001"].accuracy == 0.85
    assert suite.experiments["exp_002"].model_params.buffer_size == 1024
