if __name__ == '__main__':
    from pathlib import Path
    from django.core.management.utils import get_random_secret_key

    secret_key = get_random_secret_key()
    text = 'SECRET_KEY = \'{}\''.format(secret_key)

    parent_path = Path(__file__).resolve().parent
    filepath = parent_path / 'local_settings.py'
    with open(filepath, 'w+', encoding='utf-8') as f:
        f.write(text)