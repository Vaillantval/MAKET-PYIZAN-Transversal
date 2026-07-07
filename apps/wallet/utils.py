import secrets

# Alphabet sans caractères ambigus (0/O, 1/I)
_CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generer_code_bon_cadeau() -> str:
    """Code lisible et non devinable : MKP-XXXX-XXXX-XXXX."""
    groupes = [
        ''.join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
        for _ in range(3)
    ]
    return 'MKP-' + '-'.join(groupes)
