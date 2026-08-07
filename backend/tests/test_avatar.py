"""Tests for agent avatar upload: validation, compression, serving, removal."""
import io

from PIL import Image


def _png_bytes(size: int = 64) -> bytes:
    """Generate a solid-color PNG of `size`x`size` pixels."""
    buf = io.BytesIO()
    Image.new("RGBA", (size, size), (79, 70, 229, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _gif_bytes(frames: int = 3, size: int = 64) -> bytes:
    """Generate a tiny animated GIF (each frame a different solid color)."""
    imgs = [
        Image.new("RGB", (size, size), ((i * 60) % 255, 70, 229)) for i in range(frames)
    ]
    out = io.BytesIO()
    imgs[0].save(out, format="GIF", save_all=True, append_images=imgs[1:], duration=80, loop=0)
    return out.getvalue()


def _upload(client, headers, agent_id: int, data: bytes, content_type: str = "image/png"):
    return client.put(
        f"/api/agents/{agent_id}/avatar",
        headers=headers,
        files={"file": ("avatar.png", data, content_type)},
    )


def _create_agent(client, headers) -> int:
    res = client.post(
        "/api/agents",
        headers=headers,
        json={"name": "Avatar Bot", "description": "test"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_upload_avatar_compresses_to_webp(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    res = _upload(client, headers, agent_id, _png_bytes())
    assert res.status_code == 200, res.text
    body = res.json()
    assert f"/api/public/agents/{agent_id}/avatar?v=" in body["avatar_url"]

    # Served image is WebP, resized to at most 512px.
    img = client.get(f"/api/public/agents/{agent_id}/avatar")
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/webp"
    served = Image.open(io.BytesIO(img.content))
    assert served.format == "WEBP"
    assert max(served.size) <= 512


def test_upload_downscales_large_image(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    res = _upload(client, headers, agent_id, _png_bytes(size=2048))
    assert res.status_code == 200, res.text
    served = Image.open(io.BytesIO(client.get(f"/api/public/agents/{agent_id}/avatar").content))
    assert max(served.size) <= 512


def test_upload_rejects_wrong_content_type(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    res = _upload(client, headers, agent_id, b"not an image", content_type="text/plain")
    assert res.status_code == 422


def test_upload_rejects_non_image_bytes(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    res = _upload(client, headers, agent_id, b"this is not an image at all")
    assert res.status_code == 422
    assert "valid image" in res.json()["detail"]


def test_upload_rejects_oversized_file(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    monkeypatch.setattr("app.routers.agents.AVATAR_MAX_SIZE", 64)  # 64 bytes
    res = _upload(client, headers, agent_id, _png_bytes())
    assert res.status_code == 413


def test_upload_with_empty_content_type_sniffs_format(client, auth_headers):
    """An upload with no declared content type is sniffed by Pillow."""
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    res = client.put(
        f"/api/agents/{agent_id}/avatar",
        headers=headers,
        files={"file": ("photo", _png_bytes(), "")},
    )
    assert res.status_code == 200, res.text


def test_upload_rejects_unsupported_format_despite_png_content_type(client, auth_headers):
    """A BMP pretending to be a PNG is rejected by the format sniff."""
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 20, 30)).save(buf, format="BMP")
    res = _upload(client, headers, agent_id, buf.getvalue(), content_type="image/png")
    assert res.status_code == 422
    assert "GIF, PNG or JPG" in res.json()["detail"]


def test_replace_and_remove_avatar(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    url_before: str | None = None
    for size in (64, 128):
        res = _upload(client, headers, agent_id, _png_bytes(size=size))
        assert res.status_code == 200, res.text
        # Replace busts the browser cache: the avatar URL version changes.
        if url_before is not None:
            assert res.json()["avatar_url"] != url_before
            assert "?v=" in res.json()["avatar_url"]
        url_before = res.json()["avatar_url"]
        assert client.get(f"/api/public/agents/{agent_id}/avatar").status_code == 200

    # Remove falls back to emoji; the public URL 404s.
    res = client.delete(f"/api/agents/{agent_id}/avatar", headers=headers)
    assert res.status_code == 200
    assert res.json()["avatar_url"] is None
    assert client.get(f"/api/public/agents/{agent_id}/avatar").status_code == 404

    # Removing again is a no-op success.
    assert client.delete(f"/api/agents/{agent_id}/avatar", headers=headers).status_code == 200


def test_upload_animated_gif_becomes_animated_webp(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    res = _upload(client, headers, agent_id, _gif_bytes(frames=3), content_type="image/gif")
    assert res.status_code == 200, res.text

    served = Image.open(io.BytesIO(client.get(f"/api/public/agents/{agent_id}/avatar").content))
    assert served.format == "WEBP"
    assert getattr(served, "is_animated", False) is True
    assert int(getattr(served, "n_frames", 1)) > 1


def test_upload_static_gif_works(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    buf = io.BytesIO()
    Image.new("RGBA", (64, 64), (200, 30, 30, 255)).save(buf, format="GIF")
    res = _upload(client, headers, agent_id, buf.getvalue(), content_type="image/gif")
    assert res.status_code == 200, res.text
    served = Image.open(io.BytesIO(client.get(f"/api/public/agents/{agent_id}/avatar").content))
    assert getattr(served, "is_animated", False) is False


def test_upload_preserves_transparency(client, auth_headers):
    """A transparent PNG must keep its alpha channel (floating look)."""
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    for x in range(64):
        for y in range(64):
            if (x - 32) ** 2 + (y - 32) ** 2 <= 20**2:
                img.putpixel((x, y), (79, 70, 229, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    res = _upload(client, headers, agent_id, buf.getvalue())
    assert res.status_code == 200, res.text

    served = Image.open(
        io.BytesIO(client.get(f"/api/public/agents/{agent_id}/avatar").content)
    ).convert("RGBA")
    corner = served.getpixel((2, 2))
    center = served.getpixel((32, 32))
    assert isinstance(corner, tuple) and corner[3] < 10  # corner stays transparent
    assert isinstance(center, tuple) and center[3] == 255  # center opaque


def test_upload_rejects_too_many_gif_frames(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    monkeypatch.setattr("app.services.avatar.AVATAR_MAX_FRAMES", 1)
    res = _upload(client, headers, agent_id, _gif_bytes(frames=3), content_type="image/gif")
    assert res.status_code == 422
    assert "too many frames" in res.json()["detail"]


def test_upload_avatar_kind_template(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)

    res = client.put(
        f"/api/agents/{agent_id}/avatar",
        headers=headers,
        files={"file": ("a.gif", _gif_bytes(frames=3), "image/gif")},
        data={"kind": "template"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["avatar_kind"] == "template"


def test_upload_avatar_default_kind_is_photo(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)
    res = _upload(client, headers, agent_id, _png_bytes())
    assert res.status_code == 200, res.text
    assert res.json()["avatar_kind"] == "photo"


def test_upload_avatar_rejects_invalid_kind(client, auth_headers):
    headers, _ = auth_headers
    agent_id = _create_agent(client, headers)
    res = client.put(
        f"/api/agents/{agent_id}/avatar",
        headers=headers,
        files={"file": ("a.png", _png_bytes(), "image/png")},
        data={"kind": "bogus"},
    )
    assert res.status_code == 422
    assert "kind" in res.json()["detail"]


def test_avatar_404_for_unknown_agent(client):
    assert client.get("/api/public/agents/999999/avatar").status_code == 404
