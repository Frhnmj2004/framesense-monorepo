"""Model loader tests with mocks."""
import pytest
import torch
from unittest.mock import Mock, patch, MagicMock

from app.config import Config
from core.model_loader import check_cuda_availability, load_model
from infra.exceptions import ModelLoadError


@patch('torch.cuda.is_available')
def test_check_cuda_available(mock_cuda_available):
    """Test CUDA availability check when CUDA is available."""
    mock_cuda_available.return_value = True
    with patch('torch.cuda.get_device_name', return_value="Test GPU"):
        device = check_cuda_availability(require_gpu=True)
        assert device == "cuda"


@patch('torch.cuda.is_available')
def test_check_cuda_not_available_require_gpu(mock_cuda_available):
    """Test CUDA check fails when GPU required but not available."""
    mock_cuda_available.return_value = False
    with pytest.raises(ModelLoadError):
        check_cuda_availability(require_gpu=True)


@patch('torch.cuda.is_available')
def test_check_cuda_not_available_no_require(mock_cuda_available):
    """Test CUDA check returns CPU when GPU not required."""
    mock_cuda_available.return_value = False
    device = check_cuda_availability(require_gpu=False)
    assert device == "cpu"


@patch('core.model_loader.Sam3Processor')
@patch('core.model_loader.Sam3Model')
@patch('core.model_loader.check_cuda_availability')
def test_load_model_success(mock_check_cuda, mock_model_class, mock_processor_class):
    """Test successful model loading."""
    # Setup mocks
    mock_check_cuda.return_value = "cuda"
    mock_model = MagicMock()
    mock_model.eval = MagicMock()
    mock_model.to = MagicMock(return_value=mock_model)
    mock_model_class.from_pretrained = MagicMock(return_value=mock_model)
    mock_processor = MagicMock()
    mock_processor_class.from_pretrained = MagicMock(return_value=mock_processor)
    
    # Create config
    config = Config(model_path="facebook/sam3", require_gpu=True)
    
    # Load model
    model, processor, device = load_model(config)
    
    # Assertions
    assert device == "cuda"
    assert model == mock_model
    assert processor == mock_processor
    mock_model.to.assert_called_once_with("cuda")
    mock_model.eval.assert_called_once()


@patch('core.model_loader.Sam3Processor')
@patch('core.model_loader.Sam3Model')
@patch('core.model_loader.check_cuda_availability')
def test_load_model_failure(mock_check_cuda, mock_model_class, mock_processor_class):
    """Test model loading failure."""
    mock_check_cuda.return_value = "cuda"
    mock_model_class.from_pretrained.side_effect = Exception("Model load failed")
    
    config = Config(model_path="invalid/path", require_gpu=True)
    
    with pytest.raises(ModelLoadError):
        load_model(config)
