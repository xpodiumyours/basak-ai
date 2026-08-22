"""tests/test_tools.py — Tools modülü testleri.

Her tool'un doğru çalıştığını doğrular:
- web_search: DuckDuckGo araması
- add_task: Görev ekleme
- list_tasks: Görev listeleme
- complete_task: Görev tamamlama
- save_note: Not kaydetme
"""

import json
import os
import sys
import tempfile

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.web_search import web_search
from tools.tasks import add_task, list_tasks, complete_task
from tools.notes import save_note
from tools.executor import calistir
from tools.definitions import TOOLS


class TestWebSearch:
    """web_search tool testleri."""

    def test_bos_sorgu(self):
        """Boş sorgu hata döndürmeli."""
        sonuc = web_search("")
        assert "error" in sonuc

    def test_bosluk_sorgu(self):
        """Sadece boşluklardan oluşan sorgu hata döndürmeli."""
        sonuc = web_search("   ")
        assert "error" in sonuc

    def test_normal_sorgu(self):
        """Normal bir sorgu result veya error döndürmeli."""
        sonuc = web_search("Python programlama dili")
        assert "result" in sonuc or "error" in sonuc


class TestTasks:
    """Görev tool testleri."""

    def test_add_task(self):
        """Görev ekleme başarılı olmalı."""
        gorevler_file = tempfile.mktemp(suffix=".json")
        try:
            with open(gorevler_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            sonuc = add_task("Test görevi", gorevler_file)
            assert "result" in sonuc
            assert "Test görevi" in sonuc["result"]
            with open(gorevler_file, "r", encoding="utf-8") as f:
                gorevler = json.load(f)
            assert len(gorevler) == 1
            assert gorevler[0]["text"] == "Test görevi"
        finally:
            if os.path.exists(gorevler_file):
                os.unlink(gorevler_file)

    def test_add_task_bos(self):
        """Boş görev açıklaması hata döndürmeli."""
        gorevler_file = tempfile.mktemp(suffix=".json")
        try:
            with open(gorevler_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            sonuc = add_task("", gorevler_file)
            assert "error" in sonuc
        finally:
            if os.path.exists(gorevler_file):
                os.unlink(gorevler_file)

    def test_list_tasks_bos(self):
        """Boş görev listesi mesajı döndürmeli."""
        gorevler_file = tempfile.mktemp(suffix=".json")
        try:
            with open(gorevler_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            sonuc = list_tasks(gorevler_file)
            assert "result" in sonuc
        finally:
            if os.path.exists(gorevler_file):
                os.unlink(gorevler_file)

    def test_list_tasks_yok(self):
        """Dosya yoksa mesaj döndürmeli."""
        sonuc = list_tasks("/tmp/nonexistent.json")
        assert "result" in sonuc

    def test_complete_task(self):
        """Görev tamamlama başarılı olmalı."""
        gorevler_file = tempfile.mktemp(suffix=".json")
        try:
            with open(gorevler_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            add_task("Tamamlanacak görev", gorevler_file)
            sonuc = complete_task(1, gorevler_file)
            assert "result" in sonuc
            assert "tamamlandı" in sonuc["result"]
        finally:
            if os.path.exists(gorevler_file):
                os.unlink(gorevler_file)

    def test_complete_task_bulunamadi(self):
        """Var olmayan görev için hata döndürmeli."""
        gorevler_file = tempfile.mktemp(suffix=".json")
        try:
            with open(gorevler_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            sonuc = complete_task(999, gorevler_file)
            assert "error" in sonuc
        finally:
            if os.path.exists(gorevler_file):
                os.unlink(gorevler_file)


class TestNotes:
    """Not tool testleri."""

    def test_save_note(self):
        """Not kaydetme başarılı olmalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = save_note("Test Notu", "Bu bir test notudur", tmpdir)
            assert "result" in sonuc
            dosyalar = os.listdir(tmpdir)
            # save_note hem not dosyasi hem INDEX.md olusturur
            assert "test-notu.md" in dosyalar
            assert "INDEX.md" in dosyalar

    def test_save_note_bos_baslik(self):
        """Boş başlık hata döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = save_note("", "içerik", tmpdir)
            assert "error" in sonuc

    def test_save_note_bos_icerik(self):
        """Boş içerik hata döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = save_note("Başlık", "", tmpdir)
            assert "error" in sonuc


class TestExecutor:
    """calistir fonksiyonu testleri."""

    def test_bilinmeyen_tool(self):
        """Bilinmeyen tool için hata döndürmeli."""
        sonuc = calistir("nonexistent_tool", {})
        assert "error" in sonuc

    def test_web_search_calistir(self):
        """web_search executor üzerinden çalışmalı."""
        sonuc = calistir("web_search", {"query": "test"})
        assert "result" in sonuc or "error" in sonuc

    def test_list_tasks_calistir(self):
        """list_tasks executor üzerinden çalışmalı."""
        gorevler_file = tempfile.mktemp(suffix=".json")
        try:
            with open(gorevler_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            sonuc = calistir("list_tasks", {}, gorevler_file=gorevler_file)
            assert "result" in sonuc
        finally:
            if os.path.exists(gorevler_file):
                os.unlink(gorevler_file)


class TestToolDefinitions:
    """Tool tanımları testleri."""

    def test_tools_listesi_dogru(self):
        """TOOLS listesi 11 tool icermeli (video_analyze eklendi)."""
        assert len(TOOLS) == 11

    def test_tool_isimleri(self):
        """Tool isimleri doğru olmalı."""
        isimler = [t["function"]["name"] for t in TOOLS]
        assert "web_search" in isimler
        assert "add_task" in isimler
        assert "list_tasks" in isimler
        assert "complete_task" in isimler
        assert "save_note" in isimler

    def test_tool_format(self):
        """Her tool doğru formatta olmalı."""
        for tool in TOOLS:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
