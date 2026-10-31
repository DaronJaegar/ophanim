"""Has this password appeared in a data breach? (Bruce, Module A)
k-anonymity: only the first 5 characters of the SHA-1 hash leave the laptop."""
import hashlib, requests

def times_pwned(password):
    h = hashlib.sha1(password.encode()).hexdigest().upper()
    r = requests.get(f"https://api.pwnedpasswords.com/range/{h[:5]}", timeout=10)
    for line in r.text.splitlines():
        suffix, count = line.split(":")
        if suffix == h[5:]:
            return int(count)
    return 0
