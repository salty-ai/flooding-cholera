"""Pytest tests for infrastructure-error detection.

Covers:
  * stream text betraying a provider-side overload → detected
  * a normal, clean answer → not detected
  * an exception whose text carries an infra marker (e.g. HTTP 429) → detected
  * agent_service.py's swallowed-exception text ('Sorry, an error occurred: ...')
    surfacing only in the stream → detected
"""

import os
import sys

# Make the harness dir importable when pytest runs from anywhere.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from infra_detect import _is_infra_error


def test_overloaded_in_full_stream_is_infra_error():
    result = {
        "full_stream": "Thinking...\nSorry, an error occurred: Service temporarily overloaded, please retry.",
        "text_answer": "",
    }
    assert _is_infra_error(result, None) is True


def test_normal_answer_is_not_infra_error():
    result = {
        "full_stream": "Here is your dashboard showing cases by LGA.",
        "text_answer": "Here is your dashboard showing cases by LGA.",
    }
    assert _is_infra_error(result, None) is False


def test_http_429_exception_is_infra_error():
    exc = Exception("HTTP 429 rate limit")
    assert _is_infra_error({}, exc) is True


def test_swallowed_error_text_is_infra_error():
    result = {
        "full_stream": "Sorry, an error occurred: APIConnectionError",
        "text_answer": "Sorry, an error occurred: APIConnectionError",
    }
    assert _is_infra_error(result, None) is True


def test_data_table_with_status_codes_is_not_infra_error():
    result = {
        "full_stream": (
            "Here is the case count by status code:\n"
            "| status_code | timeout | count |\n"
            "| 503 | 30 | 12 |\n"
            "| 429 | 15 | 7 |\n"
        ),
        "text_answer": "Case counts: 503 occurred 12 times, 429 occurred 7 times.",
    }
    assert _is_infra_error(result, None) is False
