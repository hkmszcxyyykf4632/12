import pytest
from football.company_leaders import normalize_leaders


def test_exact_company_current_chair_and_identity_checked_photo():
    row = {'SECUCODE': '00700.HK', 'PERSON_CODE': 'a', 'PERSON_NAME': '马化腾', 'POSITION_NAME': '董事会主席',
           'INCUMBENT_START_DATE': '1999-12-24', 'RESUME': '负责策略。毕业于大学。曾任工程师。', 'HIGH_DEGREE': '本科'}
    parsed = normalize_leaders([row, row, {**row, 'PERSON_NAME': '副主席', 'PERSON_CODE': 'b', 'POSITION_NAME': '副董事会主席'},
                                {**row, 'PERSON_CODE': 'c', 'INCUMBENT_END_DATE': '2020-01-01'}], '00700', '', '2026-11-17')
    assert len(parsed) == 1 and parsed[0]['photo']['source'].startswith('https://www.tencent.com/')
    assert parsed[0]['education'] == ['毕业于大学']
    with pytest.raises(ValueError):
        normalize_leaders([row], '00005', '', '2026-11-17')


def test_non_chair_ceo_and_future_appointment_not_substituted():
    base = {'SECUCODE': '00005.HK', 'PERSON_NAME': '甲', 'PERSON_CODE': '1'}
    assert not normalize_leaders([{**base, 'POSITION_NAME': '行政总裁'}], '00005', '乙', '2026-11-17')
    assert not normalize_leaders([{**base, 'POSITION_NAME': '董事长', 'INCUMBENT_START_DATE': '2027-01-01'}], '00005', '甲', '2026-11-17')
