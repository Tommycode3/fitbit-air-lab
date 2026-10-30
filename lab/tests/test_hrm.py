import pytest

from lab.hrm import parse_hrm


def test_uint8_no_extras():
    m = parse_hrm(bytes([0x00, 72]))
    assert (m.bpm, m.contact, m.energy_kj, m.rr_ms) == (72, None, None, [])


def test_uint16_hr():
    m = parse_hrm(bytes([0x01, 0x2C, 0x01]))  # 300 bpm
    assert m.bpm == 300


def test_contact_supported_absent_and_present():
    assert parse_hrm(bytes([0x04, 60])).contact is False
    assert parse_hrm(bytes([0x06, 60])).contact is True
    assert parse_hrm(bytes([0x02, 60])).contact is None  # bit1 without bit2 = not supported


def test_energy_and_rr():
    # flags: contact detected + energy + RR ; bpm 65 ; energy 500 kJ ; RR 1024 and 512 (=1000 ms, 500 ms)
    data = bytes([0x1E, 65, 0xF4, 0x01, 0x00, 0x04, 0x00, 0x02])
    m = parse_hrm(data)
    assert m.bpm == 65 and m.contact is True and m.energy_kj == 500
    assert m.rr_ms == [1000.0, 500.0]


def test_rr_with_uint16_hr():
    m = parse_hrm(bytes([0x11, 0x50, 0x00, 0x33, 0x03]))  # bpm 80, RR 819/1024 s
    assert m.bpm == 80
    assert m.rr_ms == pytest.approx([799.8046875])


def test_malformed():
    with pytest.raises(ValueError):
        parse_hrm(bytes([0x00]))
    with pytest.raises(ValueError):
        parse_hrm(bytes([0x10, 60, 0x01]))
