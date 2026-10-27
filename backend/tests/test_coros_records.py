import json
import pytest
from integrations.coros_records import CorosResponseError, parse_sport_records


def response(text):
    return {'content': [{'type': 'text', 'text': json.dumps(text)}], 'isError': False}


SAMPLE = '''Sport Records — 2026-10-20 to 2026-10-27 (1 records)
========================

1. Outdoor Run — 2026-10-26
   Time Window: startTimestamp=1793011716 | endTimestamp=1793015517
   LabelId: 123456789 | SportType: 100
'''


def test_convert_utc_and_stable_id():
    result = parse_sport_records(response(SAMPLE))
    assert result == [{'source': 'coros', 'source_id': '123456789',
                       'occurred_at': '2026-10-26T10:48:36.000000+00:00',
                       'text': 'Outdoor Run — 2026-10-26', 'sport_type': 100}]


def test_empty_result_and_fail_closed():
    assert parse_sport_records(response('Sport Records (0 records)\n')) == []
    for invalid in (SAMPLE.replace('LabelId:', 'Missing:'), SAMPLE.replace('(1 records)', '(2 records)')):
        with pytest.raises(CorosResponseError):
            parse_sport_records(response(invalid))
    with pytest.raises(CorosResponseError):
        parse_sport_records({'isError': True, 'content': []})
