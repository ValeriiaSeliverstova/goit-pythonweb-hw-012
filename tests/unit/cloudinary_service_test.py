# tests/unit/cloudinary_service_test.py
from types import SimpleNamespace
from src import cloudinary_service


def test_upload_user_avatar(monkeypatch):
    calls = {"upload_kwargs": None}

    class Uploader:
        def upload(self, file_obj, **kwargs):
            calls["upload_kwargs"] = kwargs
            return {"secure_url": "https://x/y.jpg", "public_id": "pid"}

        def destroy(self, public_id, **kwargs):
            return {}

    class Api:
        def delete_resources(self, ids, **kwargs):
            return {}

    monkeypatch.setattr(
        cloudinary_service,
        "cloudinary",
        SimpleNamespace(uploader=Uploader(), api=Api()),
    )

    url, pid = cloudinary_service.upload_user_avatar(object(), 123)

    assert url == "https://x/y.jpg"
    assert pid == "pid"
    assert isinstance(calls["upload_kwargs"], dict)  # proves kwargs were accepted


def test_delete_asset(monkeypatch):
    calls = {"api": None, "uploader": None}

    class Uploader:
        def upload(self, file_obj, **kwargs):
            return {"secure_url": "https://x/y.jpg", "public_id": "pid"}

        def destroy(self, public_id, **kwargs):
            calls["uploader"] = public_id
            return {}

    class Api:
        def delete_resources(self, ids, **kwargs):
            calls["api"] = ids
            return {}

    monkeypatch.setattr(
        cloudinary_service,
        "cloudinary",
        SimpleNamespace(uploader=Uploader(), api=Api()),
    )

    cloudinary_service.delete_asset("pid")

    assert calls["api"] == ["pid"] or calls["uploader"] == "pid"
