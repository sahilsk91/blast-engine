import re
import dns.resolver

def is_valid_syntax(email: str) -> bool:
    """Basic syntax validation"""
    # Reject anything with suspicious trailing characters like .comInv
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,63}$'
    if not re.match(pattern, email):
        return False
        
    # Extra check for common snippet parsing errors
    bad_endings = ['with', 'comor', 'cominv', 'compro', 'comacc', 'comph', 'comint']
    for bad in bad_endings:
        if email.lower().endswith(bad):
            return False
            
    return True

def has_mx_record(domain: str) -> bool:
    """Check if the domain actually has mail servers configured"""
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return len(records) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout, Exception):
        return False

def verify_email(email: str) -> dict:
    """
    Validates an email address.
    Returns: {"valid": bool, "reason": str}
    """
    email = email.strip()
    
    if not is_valid_syntax(email):
        return {"valid": False, "reason": "invalid_syntax"}
        
    try:
        domain = email.split('@')[1]
    except IndexError:
        return {"valid": False, "reason": "invalid_syntax"}
        
    if not has_mx_record(domain):
        return {"valid": False, "reason": "no_mx_record"}
        
    return {"valid": True, "reason": "valid"}

if __name__ == "__main__":
    tests = [
        "test@gmail.com", 
        "bademail@outlook.comInv", 
        "fake@thisdomaindoesnotexist12345.com",
        "rusk.victoria@gmail.com"
    ]
    for t in tests:
        v = verify_email(t)
        print(f"{t}: {v}")
