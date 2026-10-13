from pathlib import Path
import pytest
from src import file_manager


class MockUploadedFile:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self.content = content

    def getvalue(self) -> bytes:
        return self.content


def test_format_bytes():
    assert file_manager.format_bytes(500) == "500 B"
    assert file_manager.format_bytes(1024) == "1.0 KB"
    assert file_manager.format_bytes(1024 * 1024) == "1.0 MB"
    assert file_manager.format_bytes(1024 * 1024 * 1024) == "1.00 GB"


def test_list_csv_files_and_classification(tmp_path):
    (tmp_path / "patients.csv").write_text("Id,BIRTHDATE\n1,1980-01-01\n")
    (tmp_path / "encounters.csv").write_text("Id,PATIENT,START\ne1,1,2020-01-01\n")
    (tmp_path / "custom.csv").write_text("a,b\n1,2\n")
    (tmp_path / "not_a_csv.txt").write_text("hello")

    files = file_manager.list_dataset_csv_files(tmp_path)
    assert len(files) == 3
    names = {f["name"] for f in files}
    assert names == {"patients.csv", "encounters.csv", "custom.csv"}

    p_info = next(f for f in files if f["name"] == "patients.csv")
    assert p_info["is_required"] is True
    assert "Demographics" in p_info["role"]

    c_info = next(f for f in files if f["name"] == "custom.csv")
    assert c_info["is_required"] is False
    assert "Custom" in c_info["role"]


def test_save_uploaded_csv(tmp_path):
    mock = MockUploadedFile("medications.csv", b"Id,PATIENT\nm1,p1\n")
    ok, msg = file_manager.save_uploaded_csv(tmp_path, mock)
    assert ok is True
    assert (tmp_path / "medications.csv").exists()
    assert (tmp_path / "medications.csv").read_bytes() == b"Id,PATIENT\nm1,p1\n"

    # Reject non-csv
    bad_mock = MockUploadedFile("malicious.exe", b"binary")
    ok2, msg2 = file_manager.save_uploaded_csv(tmp_path, bad_mock)
    assert ok2 is False
    assert "not a CSV" in msg2


def test_delete_csv_file(tmp_path):
    target = tmp_path / "sample.csv"
    target.write_text("test")
    assert target.exists()

    ok, msg = file_manager.delete_csv_file(target)
    assert ok is True
    assert not target.exists()

    # Deleting non-existent file returns False gracefully
    ok2, msg2 = file_manager.delete_csv_file(target)
    assert ok2 is False
