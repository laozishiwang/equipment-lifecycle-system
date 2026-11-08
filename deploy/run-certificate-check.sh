#!/usr/bin/env bash
set -u
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
result=$(python3 "$script_dir/check_live_certificate.py" "$@" 2>&1)
status=$?
case "$status" in
  0) level=user.info ;;
  1) level=user.warning ;;
  *) level=user.err ;;
esac
if ! logger -t equipment-certificate-check -p "$level" -- "$result"; then
  printf 'certificate_status=error unable to write system log\n' >&2
  exit 2
fi
printf '%s\n' "$result"
exit "$status"
