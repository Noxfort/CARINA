import os
import pytest
from unittest.mock import MagicMock, patch
from slm.semantic_transducer import SemanticTransducer

@pytest.fixture(autouse=True)
def mock_llama_cpp_module():
    mock_module = MagicMock()
    with patch.dict("sys.modules", {"llama_cpp": mock_module}):
        yield mock_module

@patch("torch.cuda.is_available", return_value=False)
def test_transducer_device_init_no_cuda(mock_cuda):
    transducer = SemanticTransducer(model_path="dummy_path.gguf")
    assert transducer.device_setting == "cpu"
    assert transducer.gpu_layers == 0

@patch("torch.cuda.is_available", return_value=True)
@patch("torch.cuda.mem_get_info", return_value=(4 * 1024 * 1024 * 1024, 8 * 1024 * 1024 * 1024), create=True)
def test_transducer_device_init_sufficient_vram(mock_mem, mock_cuda):
    transducer = SemanticTransducer(model_path="dummy_path.gguf")
    assert transducer.device_setting == "gpu"
    assert transducer.gpu_layers == -1

@patch("torch.cuda.is_available", return_value=True)
@patch("torch.cuda.mem_get_info", return_value=(2 * 1024 * 1024 * 1024, 8 * 1024 * 1024 * 1024), create=True)
def test_transducer_device_init_insufficient_vram(mock_mem, mock_cuda):
    transducer = SemanticTransducer(model_path="dummy_path.gguf")
    assert transducer.device_setting == "cpu"
    assert transducer.gpu_layers == 0

@patch("torch.cuda.is_available", return_value=True)
@patch("torch.cuda.mem_get_info", side_effect=Exception("Driver error"), create=True)
def test_transducer_device_init_vram_error(mock_mem, mock_cuda):
    transducer = SemanticTransducer(model_path="dummy_path.gguf")
    # Should fallback to gpu / -1 layers as best effort
    assert transducer.device_setting == "gpu"
    assert transducer.gpu_layers == -1

@patch("slm.model_loader.os.path.exists", return_value=True)
@patch("torch.cuda.is_available", return_value=False)
def test_transducer_load_resources_cpu(mock_cuda, mock_exists, mock_llama_cpp_module):
    mock_llama = mock_llama_cpp_module.Llama
    mock_llama.reset_mock()
    transducer = SemanticTransducer(model_path="dummy_path.gguf")
    transducer.load_resources()
    mock_llama.assert_called_once_with(
        model_path="dummy_path.gguf",
        n_ctx=8192,
        n_gpu_layers=0,
        verbose=False
    )

@patch("slm.model_loader.os.path.exists", return_value=True)
@patch("torch.cuda.is_available", return_value=True)
@patch("torch.cuda.mem_get_info", return_value=(4 * 1024 * 1024 * 1024, 8 * 1024 * 1024 * 1024), create=True)
def test_transducer_load_resources_gpu(mock_mem, mock_cuda, mock_exists, mock_llama_cpp_module):
    mock_llama = mock_llama_cpp_module.Llama
    mock_llama.reset_mock()
    transducer = SemanticTransducer(model_path="dummy_path.gguf")
    transducer.load_resources()
    mock_llama.assert_called_once_with(
        model_path="dummy_path.gguf",
        n_ctx=8192,
        n_gpu_layers=-1,
        verbose=False
    )

@patch("slm.model_loader.os.path.exists", return_value=True)
@patch("torch.cuda.is_available", return_value=True)
@patch("torch.cuda.mem_get_info", return_value=(4 * 1024 * 1024 * 1024, 8 * 1024 * 1024 * 1024), create=True)
def test_transducer_load_resources_gpu_fallback(mock_mem, mock_cuda, mock_exists, mock_llama_cpp_module):
    mock_llama = mock_llama_cpp_module.Llama
    mock_llama.reset_mock()
    # Make GPU load raise an exception, fallback to CPU
    mock_llama.side_effect = [Exception("CUDA error"), MagicMock()]
    transducer = SemanticTransducer(model_path="dummy_path.gguf")
    transducer.load_resources()
    assert mock_llama.call_count == 2
    # First call with -1, second with 0
    mock_llama.assert_any_call(
        model_path="dummy_path.gguf",
        n_ctx=8192,
        n_gpu_layers=-1,
        verbose=False
    )
    mock_llama.assert_any_call(
        model_path="dummy_path.gguf",
        n_ctx=8192,
        n_gpu_layers=0,
        verbose=False
    )

def test_transducer_build_prompt_laudo_estatistico_with_last_report():
    with patch("torch.cuda.is_available", return_value=False):
        transducer = SemanticTransducer(model_path="dummy_path.gguf")
    input_data = {
        "timestamp": "2026-07-02 00:00:00",
        "mode": "STATISTICAL_REPORT",
        "language": "pt_br",
        "attributions": {"junction_1": {"recommendation": "KEEP"}}
    }
    
    # Prompt without last_report
    messages = transducer._build_prompt(input_data)
    assert "LAST_REPORT_TEXT" not in messages[1]["content"]
    assert "CARINA v1.0 (SAS Engine)" in messages[0]["content"]
    
    # Prompt with last_report
    input_data["last_report_text"] = "This is the last report text content."
    messages_with_memory = transducer._build_prompt(input_data)
    assert "LAST_REPORT_TEXT" in messages_with_memory[1]["content"]
    assert "This is the last report text content." in messages_with_memory[1]["content"]

def test_transducer_build_prompt_with_speed_unit():
    with patch("torch.cuda.is_available", return_value=False):
        transducer = SemanticTransducer(model_path="dummy_path.gguf")
    
    # 1. speed_unit in input_data directly
    input_data = {
        "timestamp": "2026-07-02 00:00:00",
        "mode": "STATISTICAL_REPORT",
        "language": "en",
        "speed_unit": "km/h",
        "attributions": {"junction_1": {"recommendation": "KEEP"}}
    }
    messages = transducer._build_prompt(input_data)
    assert "SPEED_UNIT: [km/h]" in messages[1]["content"]
    assert "CARINA v1.0 (SAS Engine)" in messages[0]["content"]

    # 2. speed_unit in attributions (e.g. MFD flow)
    input_data_attributions = {
        "timestamp": "2026-07-02 00:00:00",
        "mode": "MFD_OPTIMIZATION",
        "language": "pt_br",
        "attributions": {"speed_unit": "mph", "data": 42}
    }
    messages = transducer._build_prompt(input_data_attributions)
    assert "SPEED_UNIT: [mph]" in messages[1]["content"]


def test_transducer_prompt_truncation_and_dynamic_max_tokens():
    with patch("torch.cuda.is_available", return_value=False):
        transducer = SemanticTransducer(model_path="dummy_path.gguf")
    
    # 1. Test prompt truncation
    input_data = {
        "timestamp": "2026-07-02 00:00:00",
        "mode": "STATISTICAL_REPORT",
        "language": "en",
        "last_report_text": "A" * 5000,
        "attributions": {"junction_1": {"recommendation": "KEEP"}}
    }
    messages = transducer._build_prompt(input_data)
    user_content = messages[1]["content"]
    assert "LAST_REPORT_TEXT" in user_content
    # Length of user_content shouldn't contain 5000 'A's because it was truncated to ~4000 chars
    assert "A" * 5000 not in user_content
    assert "A" * 4000 in user_content

    # 2. Test dynamic max_tokens calculation
    mock_model = MagicMock()
    # Mock tokenization to return a list of 2000 tokens
    mock_model.tokenize.return_value = [1] * 2000
    mock_model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "<think>thinking...</think>report content"}}]
    }
    transducer.model = mock_model
    
    res = transducer.generate_report(input_data)
    
    # Verify that max_tokens was bounded correctly
    # n_ctx (8192) - prompt_tokens (2000) - safety_buffer (128) = 6064. Cap min/max = 4096.
    mock_model.create_chat_completion.assert_called_once()
    called_kwargs = mock_model.create_chat_completion.call_args[1]
    assert called_kwargs["max_tokens"] == 4096
    assert res == "report content"

