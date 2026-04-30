import os
import pytest
from unittest.mock import patch

def test_sendgrid_api_key_is_set():
    key = os.getenv("SENDGRID_API_KEY")
    if key is None:
        pytest.skip("SENDGRID_API_KEY nicht gesetzt – kein E‑Mail‑Versand möglich, aber in Ordnung.")
    # Wenn gesetzt, muss er das richtige Format haben (beginnt mit SG.)
    assert key.startswith("SG."), "API‑Key hat nicht das erwartete Format"

def test_send_email_with_mock():
    with patch("backend.email_utils.SendGridAPIClient") as mock_sg, \
         patch("backend.email_utils.SENDGRID_API_KEY", "SG.dummy_key"):
        from backend.email_utils import send_email
        send_email("test@example.com", "Test", "Hallo Welt")
        mock_sg.assert_called_once()

def test_register_triggers_confirmation_email():
    with patch("backend.email_utils.SendGridAPIClient") as mock_sg:
        with patch("backend.email_utils.send_email") as mock_send:
            # Wir simulieren einen Registrierungs-Request
            # Dazu rufen wir direkt die Funktion auf? Besser: einen einfachen Mock-Test
            from backend.main import register
            import asyncio
            # Da register async ist, müssen wir es ausführen
            async def run_register():
                # Einen Fake-Request bauen? Nicht nötig, wir mocken die DB gleich
                pass