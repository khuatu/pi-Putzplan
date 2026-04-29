# tests/test_email.py
import pytest
from unittest.mock import patch
from backend.email_utils import send_email

def test_send_email_with_mock():
    with patch("backend.email_utils.SendGridAPIClient") as mock_sg:
        # Setze voraus, dass API-Key gesetzt ist (sonst return)
        with patch.dict("os.environ", {"SENDGRID_API_KEY": "dummy"}):
            send_email("test@example.com", "Test", "Hallo Welt")
            mock_sg.assert_called_once()