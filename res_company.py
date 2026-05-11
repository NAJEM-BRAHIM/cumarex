# -*- coding: utf-8 -*-
"""
Utilitaires CNSS Damancom
==========================
Algorithmes officiels de validation des numéros CNSS et helpers
de formatage pour le fichier BDS conforme au Cahier des Charges
Version 2 / Février 2006.
"""

# Liste des caractères ASCII acceptés par e-BDS pour les noms/prénoms/CIN
# Selon le cahier des charges section IV-8
ACCEPTED_ASCII_CHARS = set(
    ' \t'                            # Espace, Tabulation
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'    # Majuscules uniquement
    '0123456789'                     # Chiffres
)

# Plafond CNSS en vigueur (en DH)
PLAFOND_CNSS_DEFAULT = 6000.0

# SMIG approximatif (en centimes pour 26 jours)
SMIG_CENTIMES_DEFAULT = 312000  # ~3000 DH/mois

# Codes de situation et leurs rangs (cf section IV-2.3)
SITUATION_RANGS = {
    '': 0,      # Travail normal
    'SO': 1,    # Sortant
    'DE': 2,    # Décédé
    'IT': 3,    # Maternité
    'IL': 4,    # Maladie
    'AT': 5,    # Accident de Travail
    'CS': 6,    # Congé Sans salaire
    'MS': 7,    # Maintenu Sans Salaire
    'MP': 8,    # Maladie Professionnelle
}


def validate_num_affilie(num):
    """
    Valide un numéro d'affiliation CNSS (7 chiffres).
    Algorithme du cahier des charges section IV-4 C1:
    
    Le numéro d'affilié est composé de 7 chiffres (C1,C2,C3,C4,C5,C6,C7)
    Calculer (C2+C4+C6) × 2 + C1+C3+C5 = nombre de deux chiffres.
    Garder le chiffre des unités. 
    Si ce chiffre = 0 alors la clé C7 = 0
    Sinon C7 = 10 - chiffre des unités
    
    :param num: chaîne de 7 chiffres
    :return: (bool, str) - (valide, message d'erreur)
    """
    if not num:
        return False, "Numéro d'affiliation requis"
    num = str(num).strip()
    if len(num) != 7 or not num.isdigit():
        return False, "Le numéro d'affiliation doit comporter exactement 7 chiffres"
    
    digits = [int(c) for c in num]
    C1, C2, C3, C4, C5, C6, C7 = digits
    
    # (C2+C4+C6) × 2 + C1+C3+C5
    calc = (C2 + C4 + C6) * 2 + C1 + C3 + C5
    
    # Chiffre des unités
    unite = calc % 10
    
    if unite == 0:
        expected_C7 = 0
    else:
        expected_C7 = 10 - unite
    
    if C7 != expected_C7:
        return False, f"Clé de contrôle invalide. Chiffre attendu: {expected_C7}, fourni: {C7}"
    
    return True, ""


def validate_num_immatriculation(num):
    """
    Valide un numéro d'immatriculation CNSS d'un assuré (9 chiffres).
    Algorithme du cahier des charges section IV-4:
    
    Le numéro est composé de 9 chiffres (C1,C2,C3,C4,C5,C6,C7,C8,C9)
    Calculer (C2+C4+C6+C8) × 2 + C3+C5+C7 = nombre de deux chiffres.
    Garder le chiffre des unités.
    Si ce chiffre = 0 alors la clé C9 = 0
    Sinon C9 = 10 - chiffre des unités
    
    Règles:
    - Le premier chiffre doit être égal à 1 (sauf cas spéciaux)
    - "000000000" = salarié sans numéro (accepté avec CIN)
    - "999999999" = main d'œuvre occasionnelle (accepté)
    - "100000000" = REJETÉ explicitement par le portail
    
    :param num: chaîne de 9 chiffres
    :return: (bool, str) - (valide, message d'erreur)
    """
    if not num:
        return False, "Numéro d'immatriculation requis"
    num = str(num).strip()
    if len(num) != 9 or not num.isdigit():
        return False, "Le numéro d'immatriculation doit comporter exactement 9 chiffres"
    
    # Cas spéciaux
    if num == '000000000':
        return True, ""  # Salarié sans numéro
    if num == '999999999':
        return True, ""  # Main d'œuvre occasionnelle
    if num == '100000000':
        return False, "Le numéro 100000000 est explicitement rejeté par le portail"
    
    # Premier chiffre doit être 1
    if num[0] != '1':
        return False, "Le premier chiffre doit être 1 (sauf occasionnels commençant par 9)"
    
    digits = [int(c) for c in num]
    C1, C2, C3, C4, C5, C6, C7, C8, C9 = digits
    
    # (C2+C4+C6+C8) × 2 + C3+C5+C7
    calc = (C2 + C4 + C6 + C8) * 2 + C3 + C5 + C7
    
    # Chiffre des unités
    unite = calc % 10
    
    if unite == 0:
        expected_C9 = 0
    else:
        expected_C9 = 10 - unite
    
    if C9 != expected_C9:
        return False, f"Clé de contrôle invalide. Chiffre attendu: {expected_C9}, fourni: {C9}"
    
    return True, ""


def clean_text_for_bds(text, max_length=None):
    """
    Nettoie une chaîne pour qu'elle soit conforme au format e-BDS.
    Conversion en majuscules, suppression accents, caractères non autorisés.
    
    Caractères autorisés: A-Z, 0-9, espace, tabulation
    
    :param text: chaîne à nettoyer
    :param max_length: longueur maximale (truncate si dépassée)
    :return: chaîne nettoyée
    """
    if not text:
        return ''
    
    # Conversion en majuscules
    text = str(text).upper()
    
    # Suppression des accents (via translation table)
    accents_map = str.maketrans({
        'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A',
        'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
        'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
        'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
        'Ý': 'Y', 'Ÿ': 'Y',
        'Ç': 'C', 'Ñ': 'N',
        '-': ' ', "'": ' ', '.': ' ', ',': ' ',
    })
    text = text.translate(accents_map)
    
    # Filtrer uniquement les caractères autorisés
    text = ''.join(c if c in ACCEPTED_ASCII_CHARS else ' ' for c in text)
    
    # Supprimer espaces multiples
    while '  ' in text:
        text = text.replace('  ', ' ')
    text = text.strip()
    
    # Tronquer si nécessaire
    if max_length is not None:
        text = text[:max_length]
    
    return text


def format_an(value, length):
    """
    Formate une chaîne alphanumérique : majuscules, padding espaces à droite.
    
    :param value: chaîne
    :param length: longueur fixe attendue
    :return: chaîne de longueur exacte
    """
    s = clean_text_for_bds(value, max_length=length) if value else ''
    return s.ljust(length)[:length]


def format_n(value, length):
    """
    Formate une valeur numérique : padding zéros à gauche.
    
    :param value: nombre entier ou string numérique
    :param length: longueur fixe attendue
    :return: chaîne de longueur exacte
    """
    if value is None or value == '':
        s = '0'
    else:
        try:
            s = str(int(value))
        except (ValueError, TypeError):
            s = '0'
    return s.rjust(length, '0')[:length]


def format_centimes(value_dh, length):
    """
    Convertit un montant en DH (float) vers centimes (int) et formate.
    
    :param value_dh: montant en dirhams (float)
    :param length: longueur du champ
    :return: chaîne de centimes paddée à gauche par des zéros
    """
    if value_dh is None:
        centimes = 0
    else:
        centimes = int(round(float(value_dh) * 100))
    return format_n(centimes, length)


def format_period(year, month):
    """
    Formate une période au format AAAAMM.
    
    :param year: année (int ou string)
    :param month: mois 1-12
    :return: chaîne 'AAAAMM'
    """
    return f"{int(year):04d}{int(month):02d}"


def format_date(date_obj):
    """
    Formate une date au format AAAAMMJJ (8 chiffres).
    
    :param date_obj: objet date Python
    :return: chaîne 'AAAAMMJJ' ou '00000000' si None
    """
    if not date_obj:
        return '00000000'
    return date_obj.strftime('%Y%m%d')


def pad_record(content, length=260):
    """
    Pad un enregistrement à exactement `length` caractères (260 par défaut).
    
    :param content: chaîne de l'enregistrement
    :param length: longueur cible (défaut 260)
    :return: chaîne paddée
    """
    if len(content) > length:
        return content[:length]
    return content.ljust(length)
