import json
from pathlib import Path
from typing import List, Dict, Optional

def search_register(register_name: str, json_path: str = "extracted/registers.json") -> List[Dict]:
    """
    Search for registers by name.
    
    Args:
        register_name: The register name to search for (can be full name, short name, or partial match)
        json_path: Path to the registers JSON file
        
    Returns:
        List of matching register dictionaries
    """
    # Load registers from JSON
    json_file = Path(json_path)
    if not json_file.exists():
        return []
    
    with open(json_file, 'r', encoding='utf-8') as f:
        registers = json.load(f)
    
    # Normalize search term (case-insensitive)
    search_term = register_name.lower().strip()
    matches = []
    
    for register in registers:
        # Check full name
        full_name = register.get('full_name', '').lower()
        # Check short name
        short_name = register.get('short_name', '').lower()
        
        # Exact match on short name
        if short_name == search_term:
            matches.append(register)
        # Partial match on full name or short name
        elif search_term in full_name or search_term in short_name:
            matches.append(register)
        # Check if search term contains register name (reverse match)
        elif short_name and short_name in search_term:
            matches.append(register)
    
    return matches

def get_register_by_name(register_name: str, json_path: str = "extracted/registers.json") -> Optional[Dict]:
    """
    Get a single register by exact name match (prefers short name, then full name).
    
    Args:
        register_name: The register name to search for
        json_path: Path to the registers JSON file
        
    Returns:
        Register dictionary if found, None otherwise
    """
    matches = search_register(register_name, json_path)
    
    if not matches:
        return None
    
    # Prefer exact short name match
    search_term = register_name.lower().strip()
    for match in matches:
        if match.get('short_name', '').lower() == search_term:
            return match
    
    # Return first match if no exact short name match
    return matches[0]

# Example usage
if __name__ == "__main__":
    # Test search
    test_name = "Ethernet MAC address1 low register (ETH_MACA1LR)"
    results = search_register(test_name)
    
    print(f"Searching for: {test_name}")
    print(f"Found {len(results)} matches:\n")
    
    for i, reg in enumerate(results, 1):
        # Print the complete register data
        print(f"Match {i}:")
        print(json.dumps(reg, indent=2, ensure_ascii=False))
        print("\n" + "="*70 + "\n")

