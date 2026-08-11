# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems

import json
import unittest
from unittest.mock import MagicMock, patch

from src.communication.monitor_payload import MonitorPayloadBuilder
from src.communication.monitor_transport import MonitorMqttTransport
from src.communication.monitor_client import MonitorClient


class TestMonitorPayloadBuilder(unittest.TestCase):
    def test_create_payload_heartbeat(self):
        payload_str = MonitorPayloadBuilder.create_payload(category="", level="INFO", message="heartbeat")
        data = json.loads(payload_str)
        self.assertEqual(data["origin"], "Carina")
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["message"], "heartbeat")
        self.assertIn("occurred_at", data)

    def test_create_payload_incident(self):
        payload_str = MonitorPayloadBuilder.create_payload(category="HARDWARE", level="CRITICAL", message="Sensor failure")
        data = json.loads(payload_str)
        self.assertEqual(data["category"], "HARDWARE")
        self.assertEqual(data["level"], "CRITICAL")
        self.assertEqual(data["message"], "Sensor failure")


class TestMonitorMqttTransport(unittest.TestCase):
    def test_parse_host_port(self):
        host, port = MonitorMqttTransport.parse_host_port("192.168.1.10:1883")
        self.assertEqual(host, "192.168.1.10")
        self.assertEqual(port, 1883)

        host_def, port_def = MonitorMqttTransport.parse_host_port("localhost")
        self.assertEqual(host_def, "localhost")
        self.assertEqual(port_def, 1883)

    @patch("src.communication.monitor_transport.mqtt.Client")
    def test_publish_success(self, mock_mqtt_client_cls):
        mock_client = MagicMock()
        mock_mqtt_client_cls.return_value = mock_client
        mock_info = MagicMock()
        mock_client.publish.return_value = mock_info

        transport = MonitorMqttTransport(host="localhost", port=1883)
        transport.setup_mqtt()
        transport._is_connected = True

        res = transport.publish("test/topic", '{"msg": "hi"}')
        self.assertTrue(res)
        mock_client.publish.assert_called_once_with("test/topic", '{"msg": "hi"}', qos=1)


class TestMonitorClientFacade(unittest.TestCase):
    def setUp(self):
        MonitorClient._instance = None

    def tearDown(self):
        MonitorClient._instance = None

    @patch("src.communication.monitor_client.SettingsManager")
    @patch("src.communication.monitor_client.MonitorMqttTransport")
    def test_client_initialization_disabled(self, mock_transport_cls, mock_settings_cls):
        mock_settings = MagicMock()
        mock_settings.load_settings.return_value = {"monitor_enabled": "False"}
        mock_settings_cls.return_value = mock_settings

        mock_transport = MagicMock()
        mock_transport_cls.return_value = mock_transport

        client = MonitorClient(settings_manager=mock_settings)
        self.assertFalse(client.enabled)
        self.assertEqual(MonitorClient.get_instance(), client)


if __name__ == "__main__":
    unittest.main()
