# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from mfd.mfd_report_generator import MFDReportGenerator

def test_mfd_report_generator_empty_history():
    result = MFDReportGenerator.generate_report({"history": []})
    assert result["status"] == "error"
    assert "insuficientes ou incompletos" in result["message"] or "No MFD history" in result["message"]

@pytest.fixture(autouse=True)
def mock_default_settings():
    with patch('utils.settings_manager.SettingsManager.load_settings', return_value={"xai_speed_unit": "m/s"}):
        yield


@patch('slm.local_llama_transducer.LocalLlamaTransducer.generate_report', return_value="")
@patch('subprocess.run')
def test_mfd_report_generator_first_analysis(mock_run, mock_llama, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Executivo: O trânsito melhorou. Análise das 12:00..."
    mock_run.return_value = mock_proc
    
    history = [
        {
            "accumulation": 5.0,
            "production": 10.0,
            "mean_speed": 12.0,
            "efficiency": 0.8,
            "congestion_ratio": 0.1,
            "intersections": {
                "intersection_1": {
                    "accumulation": 2.0,
                    "production": 4.0,
                    "mean_speed": 10.0,
                    "queue_length": 1.5
                }
            }
        },
        {
            "accumulation": 6.0,
            "production": 12.0,
            "mean_speed": 13.0,
            "efficiency": 0.85,
            "congestion_ratio": 0.15,
            "intersections": {
                "intersection_1": {
                    "accumulation": 3.0,
                    "production": 5.0,
                    "mean_speed": 11.0,
                    "queue_length": 1.0
                }
            }
        }
    ]
    
    mfd_data = {
        "history": history,
        "peak_production": 15.0,
        "peak_accumulation": 7.0
    }
    
    result = MFDReportGenerator.generate_report(mfd_data, scenario_results_dir=str(tmp_path))
    assert result["status"] == "complete"
    assert "image_base64" in result
    assert "text_report" in result
    assert "Executivo: O trânsito melhorou. Análise das 12:00..." in result["text_report"]
    
    # Verify both analysis files were created
    last_analysis_file = os.path.join(tmp_path, "mfd_last_analysis.json")
    first_analysis_file = os.path.join(tmp_path, "mfd_first_analysis.json")
    assert os.path.exists(last_analysis_file)
    assert os.path.exists(first_analysis_file)
    
    with open(last_analysis_file, "r") as f:
        saved_data = json.load(f)
    assert "timestamp" in saved_data
    assert "global_stats" in saved_data
    assert "intersections_stats" in saved_data
    assert saved_data["intersections_stats"]["intersection_1"]["average_speed_m_s"] == 10.5
    
    with open(first_analysis_file, "r") as f:
        first_saved = json.load(f)
    assert first_saved["intersections_stats"]["intersection_1"]["average_speed_m_s"] == 10.5

    # Verify transducer input contains both comparison dimensions
    assert mock_run.called
    called_args, called_kwargs = mock_run.call_args_list[0]
    transducer_input = json.loads(called_kwargs['input'])
    
    attrs = transducer_input["attributions"]
    assert "comparison_since_last_analysis" in attrs
    assert "comparison_since_first_analysis" in attrs
    assert "intersections_current" in attrs
    assert "first_analysis_timestamp" in transducer_input
    
    # First run: both should be FIRST_ANALYSIS
    assert attrs["comparison_since_last_analysis"]["global_outcome"] == "FIRST_ANALYSIS"
    assert attrs["comparison_since_first_analysis"]["global_outcome"] == "FIRST_ANALYSIS"


@patch('slm.local_llama_transducer.LocalLlamaTransducer.generate_report', return_value="")
@patch('subprocess.run')
def test_mfd_report_generator_comparison_analysis(mock_run, mock_llama, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Comparação concluída com sucesso."
    mock_run.return_value = mock_proc

    # Seed LAST analysis
    last_analysis_file = os.path.join(tmp_path, "mfd_last_analysis.json")
    old_data = {
        "timestamp": "2026-07-02 10:00:00",
        "global_stats": {
            "average_speed_m_s": 8.0,
            "average_queue_length": 4.0,
            "average_efficiency": 0.5,
            "average_production": 5.0
        },
        "intersections_stats": {
            "intersection_1": {
                "average_speed_m_s": 7.0,
                "average_queue_length": 4.0,
                "average_production": 3.0,
                "average_accumulation": 2.0
            }
        }
    }
    with open(last_analysis_file, "w") as f:
        json.dump(old_data, f)

    # Seed FIRST analysis (global baseline)
    first_analysis_file = os.path.join(tmp_path, "mfd_first_analysis.json")
    first_data = {
        "timestamp": "2026-06-28 08:00:00",
        "global_stats": {
            "average_speed_m_s": 6.0,
            "average_queue_length": 6.0,
            "average_efficiency": 0.3,
            "average_production": 3.0
        },
        "intersections_stats": {
            "intersection_1": {
                "average_speed_m_s": 5.0,
                "average_queue_length": 7.0,
                "average_production": 2.0,
                "average_accumulation": 1.5
            }
        }
    }
    with open(first_analysis_file, "w") as f:
        json.dump(first_data, f)
        
    history = [
        {
            "accumulation": 5.0,
            "production": 10.0,
            "mean_speed": 12.0,
            "efficiency": 0.8,
            "congestion_ratio": 0.1,
            "intersections": {
                "intersection_1": {
                    "accumulation": 2.0,
                    "production": 4.0,
                    "mean_speed": 11.0,
                    "queue_length": 1.0
                }
            }
        }
    ]
    
    mfd_data = {
        "history": history,
        "peak_production": 15.0,
        "peak_accumulation": 7.0
    }
    
    result = MFDReportGenerator.generate_report(mfd_data, scenario_results_dir=str(tmp_path))
    assert result["status"] == "complete"
    
    assert mock_run.called
    called_args, called_kwargs = mock_run.call_args_list[0]
    transducer_input = json.loads(called_kwargs['input'])
    
    attrs = transducer_input["attributions"]
    
    # DIMENSION 1: Comparison since LAST analysis
    comp_last = attrs["comparison_since_last_analysis"]
    assert comp_last["last_analysis_timestamp"] == "2026-07-02 10:00:00"
    assert comp_last["global_outcome"] == "IMPROVED"
    
    inter_comp_last = comp_last["intersection_comparisons"]["intersection_1"]
    assert inter_comp_last["outcome"] == "IMPROVED"
    assert inter_comp_last["speed_change_pct"] > 0
    assert inter_comp_last["queue_change_value"] == -3.0
    assert inter_comp_last["previous_speed"] == 7.0
    assert inter_comp_last["current_speed"] == 11.0
    
    # DIMENSION 2: Comparison since FIRST analysis (global period)
    comp_first = attrs["comparison_since_first_analysis"]
    assert comp_first["first_analysis_timestamp"] == "2026-06-28 08:00:00"
    assert comp_first["global_outcome"] == "IMPROVED"
    
    inter_comp_first = comp_first["intersection_comparisons"]["intersection_1"]
    assert inter_comp_first["outcome"] == "IMPROVED"
    assert inter_comp_first["speed_change_pct"] > 0
    assert inter_comp_first["baseline_speed"] == 5.0
    assert inter_comp_first["current_speed"] == 11.0
    
    # Verify first_analysis_timestamp is passed to transducer
    assert transducer_input["first_analysis_timestamp"] == "2026-06-28 08:00:00"


@patch('slm.local_llama_transducer.LocalLlamaTransducer.generate_report', return_value="")
@patch('subprocess.run')
def test_mfd_report_generator_worsened(mock_run, mock_llama, tmp_path):
    """Test that a drop in speed is classified as WORSENED."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "O trânsito piorou."
    mock_run.return_value = mock_proc

    last_analysis_file = os.path.join(tmp_path, "mfd_last_analysis.json")
    old_data = {
        "timestamp": "2026-07-02 10:00:00",
        "global_stats": {
            "average_speed_m_s": 15.0,
            "average_queue_length": 2.0,
            "average_efficiency": 0.9,
            "average_production": 10.0
        },
        "intersections_stats": {
            "tl_A": {
                "average_speed_m_s": 14.0,
                "average_queue_length": 1.5,
                "average_production": 8.0,
                "average_accumulation": 3.0
            }
        }
    }
    with open(last_analysis_file, "w") as f:
        json.dump(old_data, f)

    # Seed first analysis with same good values
    first_analysis_file = os.path.join(tmp_path, "mfd_first_analysis.json")
    with open(first_analysis_file, "w") as f:
        json.dump(old_data, f)

    history = [
        {
            "accumulation": 8.0,
            "production": 5.0,
            "mean_speed": 5.0,
            "efficiency": 0.3,
            "congestion_ratio": 0.8,
            "intersections": {
                "tl_A": {
                    "accumulation": 5.0,
                    "production": 3.0,
                    "mean_speed": 4.0,
                    "queue_length": 10.0
                }
            }
        }
    ]

    mfd_data = {"history": history, "peak_production": 12.0, "peak_accumulation": 6.0}
    result = MFDReportGenerator.generate_report(mfd_data, scenario_results_dir=str(tmp_path))
    assert result["status"] == "complete"

    called_args, called_kwargs = mock_run.call_args_list[0]
    transducer_input = json.loads(called_kwargs['input'])
    attrs = transducer_input["attributions"]

    # Both dimensions should show WORSENED
    assert attrs["comparison_since_last_analysis"]["global_outcome"] == "WORSENED"
    assert attrs["comparison_since_first_analysis"]["global_outcome"] == "WORSENED"

    assert attrs["comparison_since_last_analysis"]["intersection_comparisons"]["tl_A"]["outcome"] == "WORSENED"
    assert attrs["comparison_since_first_analysis"]["intersection_comparisons"]["tl_A"]["outcome"] == "WORSENED"


@patch('slm.local_llama_transducer.LocalLlamaTransducer.generate_report', return_value="")
@patch('subprocess.run')
def test_mfd_first_analysis_file_not_overwritten(mock_run, mock_llama, tmp_path):
    """Verify that mfd_first_analysis.json is NOT overwritten on subsequent runs."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Report text"
    mock_run.return_value = mock_proc

    first_analysis_file = os.path.join(tmp_path, "mfd_first_analysis.json")
    original_baseline = {
        "timestamp": "2026-06-28 08:00:00",
        "global_stats": {
            "average_speed_m_s": 5.0,
            "average_queue_length": 10.0,
            "average_efficiency": 0.2,
            "average_production": 2.0
        },
        "intersections_stats": {}
    }
    with open(first_analysis_file, "w") as f:
        json.dump(original_baseline, f)

    history = [
        {
            "accumulation": 5.0, "production": 10.0, "mean_speed": 12.0,
            "efficiency": 0.8, "congestion_ratio": 0.1, "intersections": {}
        }
    ]
    mfd_data = {"history": history, "peak_production": 15.0, "peak_accumulation": 7.0}
    MFDReportGenerator.generate_report(mfd_data, scenario_results_dir=str(tmp_path))

    # First analysis file should still contain the original baseline
    with open(first_analysis_file, "r") as f:
        preserved = json.load(f)
    assert preserved["timestamp"] == "2026-06-28 08:00:00"
    assert preserved["global_stats"]["average_speed_m_s"] == 5.0


@patch('slm.local_llama_transducer.LocalLlamaTransducer.generate_report', return_value="")
@patch('subprocess.run')
@patch('utils.settings_manager.SettingsManager.load_settings')
def test_mfd_report_generator_speed_units_and_integers(mock_load_settings, mock_run, mock_llama, tmp_path):
    """Verify that speed unit conversion is correctly applied and vehicles metrics are integers."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Report with custom speed unit."
    mock_run.return_value = mock_proc
    
    # Configure speed unit as km/h
    mock_load_settings.return_value = {"xai_speed_unit": "km/h"}
    
    history = [
        {
            "accumulation": 5.4,
            "production": 10.0,
            "mean_speed": 10.0,
            "efficiency": 0.8,
            "congestion_ratio": 0.1,
            "intersections": {
                "intersection_1": {
                    "accumulation": 2.6,
                    "production": 4.0,
                    "mean_speed": 10.0,
                    "queue_length": 1.7
                }
            }
        }
    ]
    
    mfd_data = {
        "history": history,
        "peak_production": 15.0,
        "peak_accumulation": 7.3
    }
    
    result = MFDReportGenerator.generate_report(mfd_data, scenario_results_dir=str(tmp_path))
    assert result["status"] == "complete"
    
    assert mock_run.called
    called_args, called_kwargs = mock_run.call_args_list[0]
    transducer_input = json.loads(called_kwargs['input'])
    attrs = transducer_input["attributions"]
    
    # Speed unit must be 'km/h'
    assert attrs["speed_unit"] == "km/h"
    
    # 10.0 m/s * 3.6 = 36.0 km/h
    assert attrs["average_speed"] == 36.0
    
    # Vehicle count: 5.4 (avg_accum) and 7.3 (peak_accum) must be integers: 5 and 7
    assert attrs["average_accumulation_veh"] == 5
    assert attrs["critical_accumulation_veh"] == 7
    
    # Per-intersection current queue length 1.7 -> 2, average_accumulation 2.6 -> 3
    inter_current = attrs["intersections_current"]["intersection_1"]
    assert inter_current["average_queue_length"] == 2
    assert inter_current["average_accumulation"] == 3

