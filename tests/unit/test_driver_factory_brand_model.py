import pytest
from src.drivers.driver_factory import DriverFactory

def test_extract_brand_and_model_siemens():
    descr = "Siemens UTC Traffic Light Controller ST950 v4.2"
    brand, model = DriverFactory.extract_brand_and_model(descr)
    assert brand == "Siemens"
    assert model == "ST950"

def test_extract_brand_and_model_peek():
    descr = "Peek Traffic Controller M60 NTCIP 1202"
    brand, model = DriverFactory.extract_brand_and_model(descr)
    assert brand == "Peek"
    assert model == "M60"

def test_extract_brand_and_model_unknown():
    brand, model = DriverFactory.extract_brand_and_model(None)
    assert brand == "Não informado"
    assert model == "Não informado"

    brand2, model2 = DriverFactory.extract_brand_and_model("")
    assert brand2 == "Não informado"
    assert model2 == "Não informado"
