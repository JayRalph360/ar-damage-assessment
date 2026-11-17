"""
Start the AR Damage Assessment System.

    python run.py            -> HTTPS on port 8443 (needed for the phone's live camera)
    python run.py --http     -> plain HTTP on port 8000 (laptop testing only)

On first HTTPS run a self-signed certificate is created in backend/data/certs.
Open the printed https://<your-laptop-IP>:8443 address on your phone (same Wi-Fi),
tap "Advanced" -> "Proceed" on the certificate warning, then log in.

To remove the certificate warning (localhost, Cloudflare Tunnel or mkcert),
and for the Windows "Smart App Control blocked" fix, see README.md sections 1 and 1b.
"""
import datetime
import ipaddress
import os
import socket
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def make_cert(cert_dir: str, ip: str):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    os.makedirs(cert_dir, exist_ok=True)
    key_path, cert_path = os.path.join(cert_dir, "key.pem"), os.path.join(cert_dir, "cert.pem")
    ip_file = os.path.join(cert_dir, "ip.txt")
    if os.path.exists(cert_path) and os.path.exists(ip_file) and open(ip_file).read().strip() == ip:
        return key_path, cert_path
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AR Damage Assessment")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=825))
            .add_extension(x509.SubjectAlternativeName([
                x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                x509.IPAddress(ipaddress.ip_address(ip))]), critical=False)
            .sign(key, hashes.SHA256()))
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                  serialization.NoEncryption()))
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(ip_file, "w") as f:
        f.write(ip)
    return key_path, cert_path


def main():
    import uvicorn

    ip = lan_ip()
    if "--http" in sys.argv:
        print(f"\n  Laptop:  http://localhost:8000\n  (Phone live camera needs HTTPS: run without --http)\n")
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
        return
    cert_dir = os.path.join(BACKEND, "data", "certs")
    trusted = (os.path.join(cert_dir, "trusted-key.pem"), os.path.join(cert_dir, "trusted-cert.pem"))
    if all(os.path.exists(p) for p in trusted):
        key, cert = trusted          # mkcert certificate -> no browser warnings
        print("\n  Using trusted certificate (mkcert)")
    else:
        key, cert = make_cert(cert_dir, ip)
    print("\n  AR Damage Assessment System is running")
    print(f"  Laptop:  https://localhost:8443")
    print(f"  Phone:   https://{ip}:8443   (same Wi-Fi; accept the certificate warning)")
    print("  Login:   inspector / inspect123")
    if key != trusted[0]:
        print("  Browser shows 'Not secure'? See README.md section 1b to remove the warning.")
    print()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8443, ssl_keyfile=key, ssl_certfile=cert)


if __name__ == "__main__":
    main()
