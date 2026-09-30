#!/usr/bin/env python3
"""Build the password-protected review site (repo-root ``review/``) from the demo folder.

What it does
------------
* Collects the demo page (``index.html``), every local image/data/video file it references, the
  whole ``viewer/`` folder (terrain viewer page + heightmaps + textures + unit models) and the
  ``viewer3d/`` folder (interactive presentation model page + .glb).
* Adds a small "Private review · Lock" link to each HTML page.
* Packs everything into one container and encrypts it with AES-256-GCM. The key comes from the
  review password through PBKDF2-SHA256 (600,000 iterations by default) with a random salt.
* Writes ``review/bundle.enc`` (ciphertext only), ``review/index.html`` (the gate page that
  decrypts in the browser with WebCrypto), ``review/sw.js`` (the service worker that serves the
  decrypted pages under ``review/app/``) and ``review/README.md``.

The password is never written to disk by this script and must not be committed. Anyone who can
download ``bundle.enc`` gets ciphertext only, so the folder can live on a public GitHub Pages site.

Usage
-----
  REVIEW_PASSWORD='the passphrase' python3 scripts/build_review.py
  python3 scripts/build_review.py --password-file ~/ffw-review.pw
  python3 scripts/build_review.py --generate           # makes a fresh random passphrase and prints it once

Options: --base <demo folder> (default: the folder above scripts/), --out <review folder>
(default: <repo root>/review), --iterations <n> (PBKDF2 rounds), --title <gate heading>.

Container format (all big-endian): ``FFWREV1\\0`` (8) | iterations (4) | salt (16) | iv (12) |
AES-GCM ciphertext of: index length (4) | index JSON | concatenated file bytes.
Index JSON: ``[{"p": path, "t": mime type, "o": offset, "n": size}, ...]``.
"""
from __future__ import annotations

import argparse
import getpass
import json
import mimetypes
import os
import re
import secrets
import shutil
import struct
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

HERE = Path(__file__).resolve().parent
MAGIC = b"FFWREV1\x00"
REF_RE = re.compile(r'(?:src|href|poster)="([^"#?]+)')
WORDS = ("gator", "cypress", "lantern", "saucer", "castle", "moss", "swamp", "mushroom", "firefly",
         "heron", "orbit", "haunt", "ember", "willow", "comet", "marsh", "spore", "beacon", "raven",
         "tide", "pine", "meteor", "fable", "thunder", "compass", "harbor", "acorn", "nova", "cabin",
         "wander", "kettle", "summit", "ripple", "banjo", "canoe", "juniper", "signal", "prairie",
         "glacier", "velvet")
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I to keep it typeable


def generate_passphrase() -> str:
    words = [secrets.choice(WORDS).capitalize() for _ in range(3)]
    tail = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return "-".join(words + [tail])


def mime_for(path: str) -> str:
    ext = Path(path).suffix.lower()
    fixed = {".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
             ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
             ".md": "text/markdown; charset=utf-8", ".txt": "text/plain; charset=utf-8",
             ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
             ".svg": "image/svg+xml", ".glb": "model/gltf-binary", ".dxf": "application/dxf"}
    if ext in fixed:
        return fixed[ext]
    guess, _ = mimetypes.guess_type(path)
    return guess or "application/octet-stream"


def collect(base: Path) -> list[str]:
    """Relative paths (posix) of everything the demo page and the viewer need."""
    wanted: list[str] = ["index.html"]
    demo = (base / "index.html").read_text(encoding="utf-8")
    for ref in REF_RE.findall(demo):
        if ref.startswith(("http:", "https:", "data:", "mailto:", "/")):
            continue
        rel = os.path.normpath(ref).replace(os.sep, "/")
        if rel.startswith(".."):
            continue
        if (base / rel).is_file() and rel not in wanted:
            wanted.append(rel)
        elif not (base / rel).is_file():
            print(f"  warning: demo references {rel} but it is missing; skipped", file=sys.stderr)
    for folder in ("viewer", "viewer3d"):
        if not (base / folder).is_dir():
            continue
        for p in sorted((base / folder).rglob("*")):
            if p.is_file() and not p.name.startswith("."):
                rel = p.relative_to(base).as_posix()
                if rel not in wanted:
                    wanted.append(rel)
    return wanted


def lock_pill(depth: int, viewer: bool) -> str:
    up = "../" * (depth + 1)
    if viewer:
        pos = "right:16px;top:calc(108px + env(safe-area-inset-top,0px))"
    else:
        pos = "right:12px;bottom:12px"
    return (f'<a id="ffw-lock" href="{up}?lock=1" style="position:fixed;{pos};z-index:99999;'
            'font:600 12px/1 Barlow,system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;'
            'color:#f3ead8;background:rgba(20,18,14,.88);border:1px solid #3a352c;border-radius:999px;'
            'padding:8px 12px;text-decoration:none">Private review · Lock</a>\n')


def prepare_html(rel: str, data: bytes) -> bytes:
    text = data.decode("utf-8")
    depth = rel.count("/")
    pill = lock_pill(depth, viewer=rel.startswith(("viewer/", "viewer3d/")))
    if "</body>" in text:
        text = text.replace("</body>", pill + "</body>", 1)
    else:
        text += pill
    if "<head>" in text and 'name="robots"' not in text:
        text = text.replace("<head>", '<head>\n<meta name="robots" content="noindex, nofollow, noarchive">', 1)
    return text.encode("utf-8")


def build(base: Path, out: Path, password: str, iterations: int, title: str) -> dict:
    files = collect(base)
    index = []
    blobs = bytearray()
    for rel in files:
        data = (base / rel).read_bytes()
        if rel.endswith(".html"):
            data = prepare_html(rel, data)
        index.append({"p": rel, "t": mime_for(rel), "o": len(blobs), "n": len(data)})
        blobs += data
    index_json = json.dumps(index, separators=(",", ":")).encode("utf-8")
    plain = struct.pack(">I", len(index_json)) + index_json + bytes(blobs)

    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    key = kdf.derive(password.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, plain, None)

    out.mkdir(parents=True, exist_ok=True)
    (out / "bundle.enc").write_bytes(MAGIC + struct.pack(">I", iterations) + salt + iv + ct)
    gate = (HERE / "review_site" / "index.html").read_text(encoding="utf-8")
    gate = gate.replace("<h1>Florida Freedom World</h1>", f"<h1>{title}</h1>")
    (out / "index.html").write_text(gate, encoding="utf-8")
    shutil.copyfile(HERE / "review_site" / "sw.js", out / "sw.js")
    (out / "README.md").write_text(README.format(n=len(files), mb=len(plain) / 1048576,
                                                 iters=f"{iterations:,}"), encoding="utf-8")
    return {"files": len(files), "plain_bytes": len(plain), "bundle_bytes": (out / "bundle.enc").stat().st_size}


README = """# Private review site

Password-protected copy of the Florida Freedom World demo for reviewers. Everything in
`bundle.enc` is AES-256-GCM ciphertext; the key is derived in the browser from the review
password (PBKDF2-SHA256, {iters} rounds). Nothing readable is stored in this folder, so it
can sit on a public GitHub Pages site or any static host.

* `index.html`: the gate. Downloads the bundle, decrypts it with WebCrypto, hands the files to
  the service worker and opens `app/index.html`.
* `sw.js`: service worker that serves the decrypted pages from this browser's cache under
  `app/`. A locked browser is redirected back to the gate.
* `bundle.enc`: {n} files, {mb:.1f} MB before encryption (demo page, 3D viewer, images, data).
* `florida-freedom-world-review.pdf`: the whole demo as a 20-page landscape PDF (poster cover, one
  section per page), AES-256 encrypted with the same review password. Made by
  `scripts/export_pdf.js` (Chromium print of the demo page) and `scripts/encrypt_pdf.py`.

Locking: the "Private review · Lock" link on every page (or opening the gate again) wipes the
decrypted copy from the browser. Nothing is sent anywhere.

Rebuild after changing the demo or to rotate the password:

    REVIEW_PASSWORD='new passphrase' python3 reports/sausage-castle-base/scripts/build_review.py

The password is never written into the repository; share it with reviewers out of band.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", type=Path, default=HERE.parent, help="demo folder (has index.html and viewer/)")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: <repo root>/review)")
    ap.add_argument("--iterations", type=int, default=600_000)
    ap.add_argument("--title", default="Florida Freedom World")
    ap.add_argument("--password-file", type=Path, help="file whose first line is the password")
    ap.add_argument("--generate", action="store_true", help="generate a random passphrase and print it")
    args = ap.parse_args()

    base = args.base.resolve()
    out = (args.out or (base.parent.parent / "review")).resolve()

    if args.generate:
        password = generate_passphrase()
        print(f"Generated review password (shown once, not saved): {password}")
    elif args.password_file:
        password = args.password_file.read_text(encoding="utf-8").splitlines()[0].strip()
    elif os.environ.get("REVIEW_PASSWORD"):
        password = os.environ["REVIEW_PASSWORD"]
    else:
        password = getpass.getpass("Review password: ")
    if len(password) < 12:
        print("Refusing: use at least 12 characters (a long random passphrase is what protects the bundle).", file=sys.stderr)
        return 2

    print(f"Base: {base}\nOut:  {out}")
    stats = build(base, out, password, args.iterations, args.title)
    print(f"Packed {stats['files']} files, {stats['plain_bytes']/1048576:.1f} MB -> bundle.enc "
          f"{stats['bundle_bytes']/1048576:.1f} MB ({args.iterations:,} PBKDF2 rounds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
