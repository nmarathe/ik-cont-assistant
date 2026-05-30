"""Export Windows certificate store + certifi into a combined PEM bundle.

Run once to create certs/ca_bundle.pem, then set SSL_CERT_FILE in .env.
"""

import base64
import ssl
import sys
from pathlib import Path

import certifi

OUT = Path(__file__).parent.parent / "certs" / "ca_bundle.pem"
OUT.parent.mkdir(exist_ok=True)

pem_blocks: list[str] = []

# Start with certifi's well-known bundle
pem_blocks.append(Path(certifi.where()).read_text(encoding="utf-8"))

# Append every cert from the Windows CA and ROOT stores
added = 0
for store_name in ("CA", "ROOT"):
    for cert_der, encoding, _trust in ssl.enum_certificates(store_name):  # type: ignore[attr-defined]
        if encoding == "x509_asn":
            b64 = base64.encodebytes(cert_der).decode("ascii")
            pem_blocks.append(f"-----BEGIN CERTIFICATE-----\n{b64}-----END CERTIFICATE-----\n")
            added += 1

OUT.write_text("\n".join(pem_blocks), encoding="utf-8")
print(f"Written {added} Windows certs + certifi bundle -> {OUT}")
print(f'\nAdd this line to your .env:\nSSL_CERT_FILE={OUT.as_posix()}')
