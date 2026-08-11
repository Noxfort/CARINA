import pytest
import socket
import time
from unittest.mock import MagicMock, patch
from src.drivers.hardware_event_listener import SnmpTrapListener, BaseActiveEventListener

def test_extract_and_dispatch_trap():
    dispatched_events = []
    
    def mock_callback(event):
        dispatched_events.append(event)
        
    listener = SnmpTrapListener(
        port=16299,  # Use high port for testing
        get_intersection_by_ip=lambda ip: "TL_TEST_01"
    )
    listener.on_event_callback = mock_callback

    with patch("src.drivers.incident_reporter.IncidentReporter.report_trap") as mock_report_trap:
        listener.start()
        time.sleep(0.1)

        # Send test UDP Trap packet
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b"\x30\x20\x02\x01\x01\x04\x06public\xa4\x13\x06\x08Siemens ST950 Lamp Failure Error", ("127.0.0.1", 16299))
        sock.close()

        time.sleep(0.3)
        listener.stop()

        assert len(dispatched_events) > 0
        event = dispatched_events[0]
        assert event["intersection_id"] == "TL_TEST_01"
        assert event["category"] == "HARDWARE"
        assert event["source_ip"] == "127.0.0.1"
        assert event["message"] == "[TL_TEST_01] Siemens ST950 Lamp Failure Error"
        
        # Allow daemon thread time to invoke report_trap
        time.sleep(0.1)
        assert mock_report_trap.called

def test_trap_transformer_unified_payload():
    from src.drivers.trap_transformer import TrapTransformer
    
    # 1. Bracketed software alert
    payload_sw = TrapTransformer.transform("[SOFTWARE] Erro de sincronizacao de relogio", intersection_id="1116667894")
    assert payload_sw["category"] == "SOFTWARE"
    assert payload_sw["intersection_id"] == "1116667894"
    assert payload_sw["message"] == "[1116667894] Erro de sincronizacao de relogio"
    
    # 2. Bracketed hardware alert
    payload_hw = TrapTransformer.transform("[HARDWARE] Falha no detector de laco 01", intersection_id="tl_1")
    assert payload_hw["category"] == "HARDWARE"
    assert payload_hw["intersection_id"] == "tl_1"
    assert payload_hw["message"] == "[tl_1] Falha no detector de laco 01"

def test_trap_transformer_5field_mock_payload():
    from src.drivers.trap_transformer import TrapTransformer
    
    mock_payload = "TRAP|1116667894|1.3.6.1.4.1.2825.4.1.5|WARNING|[HARDWARE] Alerta de Armario Aberto: Porta do gabinete aberta"
    res = TrapTransformer.transform(mock_payload, intersection_id="DESCONHECIDO")
    assert res["intersection_id"] == "1116667894"
    assert res["category"] == "HARDWARE"
    assert res["level"] == "WARNING"
    assert res["details"] == "Alerta de Armario Aberto: Porta do gabinete aberta"
    assert res["message"] == "[1116667894] Alerta de Armario Aberto: Porta do gabinete aberta"

def test_incident_reporter_fallback_publishing():
    from src.drivers.incident_reporter import IncidentReporter
    
    trap_data = {
        "category": "HARDWARE",
        "level": "CRITICAL",
        "details": "Falha simulada no controlador",
        "message": "[1116667894] Falha simulada no controlador",
        "intersection_id": "1116667894"
    }
    
    mock_settings = {"monitor_enabled": "True", "monitor_mqtt_host": "127.0.0.1:1883"}
    
    with patch("src.utils.settings_manager.SettingsManager.load_settings", return_value=mock_settings), \
         patch("src.communication.monitor_client.MonitorClient.get_instance", return_value=None), \
         patch("paho.mqtt.client.Client") as mock_mqtt_cls:
        
        mock_mqtt_inst = MagicMock()
        mock_mqtt_cls.return_value = mock_mqtt_inst
        mock_info = MagicMock()
        mock_mqtt_inst.publish.return_value = mock_info
        
        IncidentReporter.report_trap("1116667894", "CRITICAL", trap_data)
        
        assert mock_mqtt_inst.connect.called
        assert mock_mqtt_inst.publish.called
        call_args = mock_mqtt_inst.publish.call_args
        assert call_args[0][0] == "noxfort/telemetry/"
        import json
        published_json = json.loads(call_args[0][1])
        assert published_json["category"] == "HARDWARE"
        assert published_json["message"] == "[1116667894] Falha simulada no controlador"

