"""Tests para el módulo de descarga."""

import pytest
import requests
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config import RAW_DIR, RAW_CSV
from src.downloader import download, clean_session


class TestDownload:
    """Tests de la función download()."""

    def test_download_crea_directorio(self, tmp_path, monkeypatch):
        """Verifica que se crea el directorio si no existe."""
        dest = tmp_path / "subdir" / "test.csv"
        monkeypatch.setattr("src.downloader.RAW_CSV", dest)

        mock_response = MagicMock()
        mock_response.content = b"a,b\n1,2\n"
        mock_response.raise_for_status = MagicMock()

        with patch("src.downloader.requests.get", return_value=mock_response):
            download(url="http://fake", dest=dest)

        assert dest.exists()
        assert dest.read_bytes() == b"a,b\n1,2\n"

    def test_download_falla_con_http_error(self, tmp_path):
        """Verifica que se lanza excepción ante error HTTP."""
        dest = tmp_path / "test.csv"
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")

        with patch("src.downloader.requests.get", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                download(url="http://fake", dest=dest)


class TestCleanSession:
    """Tests de clean_session()."""

    def test_clean_session_elimina_csv(self, tmp_path, monkeypatch):
        """Verifica que se eliminan los CSV de la sesión."""
        raw_dir = tmp_path / "raw"
        proc_dir = tmp_path / "processed"
        raw_dir.mkdir()
        proc_dir.mkdir()

        f1 = raw_dir / "a.csv"
        f2 = proc_dir / "b.csv"
        f1.write_text("data")
        f2.write_text("data")

        monkeypatch.setattr("src.downloader.RAW_DIR", raw_dir)
        monkeypatch.setattr("src.downloader.PROCESSED_DIR", proc_dir)

        clean_session()

        assert not f1.exists()
        assert not f2.exists()

    def test_clean_session_no_falla_si_vacio(self, tmp_path, monkeypatch):
        """Verifica que no falla si no hay archivos."""
        raw_dir = tmp_path / "raw"
        proc_dir = tmp_path / "processed"
        raw_dir.mkdir()
        proc_dir.mkdir()

        monkeypatch.setattr("src.downloader.RAW_DIR", raw_dir)
        monkeypatch.setattr("src.downloader.PROCESSED_DIR", proc_dir)

        # No debe lanzar excepción
        clean_session()