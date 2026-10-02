# Private review site

Password-protected copy of the Florida Freedom World demo for reviewers. Everything in
`bundle.enc` is AES-256-GCM ciphertext; the key is derived in the browser from the review
password (PBKDF2-SHA256, 600,000 rounds). Nothing readable is stored in this folder, so it
can sit on a public GitHub Pages site or any static host.

* `index.html`: the gate. Downloads the bundle, decrypts it with WebCrypto, hands the files to
  the service worker and opens `app/index.html`.
* `sw.js`: service worker that serves the decrypted pages from this browser's cache under
  `app/`. A locked browser is redirected back to the gate.
* `bundle.enc`: 56 files, 25.9 MB before encryption (demo page, 3D viewer, images, data).
* `florida-freedom-world-review.pdf`: the whole demo as a 20-page landscape PDF (poster cover, one
  section per page), AES-256 encrypted with the same review password. Made by
  `scripts/export_pdf.js` (Chromium print of the demo page) and `scripts/encrypt_pdf.py`.

Locking: the "Private review · Lock" link on every page (or opening the gate again) wipes the
decrypted copy from the browser. Nothing is sent anywhere.

Rebuild after changing the demo or to rotate the password:

    REVIEW_PASSWORD='new passphrase' python3 reports/sausage-castle-base/scripts/build_review.py

The password is never written into the repository; share it with reviewers out of band.
