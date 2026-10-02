#!/usr/bin/env python3
"""Encrypt a PDF for reviewers with AES-256 (PDF 2.0 encryption) under the review password.

Usage:
  REVIEW_PASSWORD='...' python3 scripts/encrypt_pdf.py <in.pdf> <out.pdf> [--title "..."]

The same password opens the PDF and the review site. The password is read from the
REVIEW_PASSWORD environment variable (or a prompt) and is never written anywhere.
"""
import argparse
import getpass
import os
import sys

from pypdf import PdfReader, PdfWriter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--title", default="Florida Freedom World: private review copy")
    ap.add_argument("--author", default="Bearded Freedom")
    a = ap.parse_args()
    pw = os.environ.get("REVIEW_PASSWORD") or getpass.getpass("Review password: ")
    if len(pw) < 12:
        print("Refusing: use at least 12 characters.", file=sys.stderr)
        return 2
    w = PdfWriter(clone_from=PdfReader(a.src))
    w.add_metadata({"/Title": a.title, "/Author": a.author})
    w.encrypt(user_password=pw, owner_password=pw, algorithm="AES-256")
    with open(a.dst, "wb") as f:
        w.write(f)

    print(f"Wrote {a.dst} ({os.path.getsize(a.dst)/1048576:.1f} MB, AES-256, opens with the review password)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
