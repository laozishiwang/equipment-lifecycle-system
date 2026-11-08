#!/usr/bin/env python3
"""Read-only preflight for the proposed production Compose deployment."""
import base64
import binascii
import ipaddress
import pathlib
import re
import socket
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent.parent
env_file = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / '.env.production'
errors = []
values = {}
try:
    for line in env_file.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            errors.append('Invalid environment file line')
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
except OSError:
    errors.append('Production environment file is not readable')

for key in ('DB_ROOT_PASSWORD', 'DB_PASSWORD', 'TOKEN_SECRET'):
    value = values.get(key, '')
    if len(value) < 24 or 'replace' in value.lower() or 'example' in value.lower():
        errors.append(f'{key} must be a unique random secret of at least 24 characters')
secrets = [values.get(k, '') for k in ('DB_ROOT_PASSWORD', 'DB_PASSWORD', 'TOKEN_SECRET')]
if all(secrets) and len(set(secrets)) != len(secrets):
    errors.append('Database and token secrets must be different')

try:
    admin_hash = base64.b64decode(values.get('ADMIN_BCRYPT_BASE64', ''), validate=True).decode('ascii')
    if not re.fullmatch(r'\$2[aby]\$(?:1[2-5])\$[./A-Za-z0-9]{53}', admin_hash) or admin_hash == '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2':
        errors.append('ADMIN_BCRYPT_BASE64 must contain a non-default bcrypt hash')
except (binascii.Error, UnicodeDecodeError, ValueError):
    errors.append('ADMIN_BCRYPT_BASE64 must contain a non-default bcrypt hash')
domain = values.get('SITE_DOMAIN', '')
try:
    address = ipaddress.ip_address(domain)
except ValueError:
    address = None
if address:
    if not address.is_global:
        errors.append('SITE_DOMAIN IP must be public')
    if values.get('PUBLIC_IP') and values['PUBLIC_IP'] != str(address):
        errors.append('SITE_DOMAIN and PUBLIC_IP must match for IP access')
elif len(domain) > 253 or not re.fullmatch(r'(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}', domain) or domain.lower().endswith('.example.com'):
    errors.append('SITE_DOMAIN must be a public IP or real fully qualified domain name')
else:
    try:
        addresses = {x[4][0] for x in socket.getaddrinfo(domain, None, type=socket.SOCK_STREAM)}
        if not addresses:
            errors.append('SITE_DOMAIN has no DNS addresses')
        expected = values.get('PUBLIC_IP', '')
        if expected:
            ipaddress.ip_address(expected)
            if expected not in addresses:
                errors.append('SITE_DOMAIN DNS does not include PUBLIC_IP')
    except (OSError, ValueError):
        errors.append('SITE_DOMAIN DNS or PUBLIC_IP is invalid')
for port in (80, 443):
    sock = socket.socket()
    try:
        sock.bind(('0.0.0.0', port))
    except OSError:
        errors.append(f'Port {port} is unavailable; check existing services')
    finally:
        sock.close()

if env_file.is_file():
    result = subprocess.run(['docker', 'compose', '--env-file', str(env_file), '-f', str(root / 'compose.production.yaml'), 'config', '-q'], cwd=root, capture_output=True, text=True)
    if result.returncode:
        errors.append('Docker Compose configuration is invalid')

for error in errors:
    print('FAIL:', error)
print('MANUAL: verify initial administrator credentials are changed before public access.')
print('MANUAL: verify TLS reachability, firewall, permissions, offsite backups and restore rehearsal.')
if errors:
    sys.exit(1)
print('Automated preflight checks passed; manual checks and acceptance are still required.')



