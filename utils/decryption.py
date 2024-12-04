import base64
import binascii
import hashlib
import msvcrt 
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import unpad
from web3 import Web3


def is_base64(s):
    if not len(s):
        return False
    try:
        if len(s) == 64:
            Web3().eth.account.from_key(s)
            return False
    except Exception:
        ...
    try:
        decoded = base64.b64decode(s)
        reencoded = base64.b64encode(decoded)
        return reencoded == s.encode()
    except Exception:
        return False


def get_cipher(password):
    salt = hashlib.sha256(password.encode('utf-8')).digest()
    key = PBKDF2(password.encode('utf-8'), salt, dkLen=32, count=1)
    return AES.new(key, AES.MODE_ECB)


def decrypt_private_key(encrypted_base64_pk, password):
    cipher = get_cipher(password)
    encrypted_pk = base64.b64decode(encrypted_base64_pk)
    decrypted_bytes = unpad(cipher.decrypt(encrypted_pk), 16)
    decrypted_hex = binascii.hexlify(decrypted_bytes).decode()
    if len(decrypted_hex) in (66, 42):
        decrypted_hex = decrypted_hex[2:]
    return '0x' + decrypted_hex


def get_password(prompt="Введите пароль для расшифровки: "):
    """
    Ввод пароля с отображением звездочек (*) вместо вводимых символов.
    Поддерживает любые печатаемые символы, включая цифры, буквы и специальные символы.

    :param prompt: Строка приглашения для ввода пароля.
    :return: Введённый пароль в виде строки.
    """
    import sys
    import os

    if os.name == 'nt':
        # Реализация для Windows
        print(prompt, end='', flush=True)
        password = ""
        while True:
            ch = msvcrt.getch()
            if ch in {b'\r', b'\n'}:
                print('')
                break
            elif ch == b'\x03':
                # Обработка Ctrl+C
                raise KeyboardInterrupt
            elif ch in {b'\x08', b'\x7f'}:
                # Обработка Backspace/Delete
                if len(password) > 0:
                    password = password[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif ch.decode('utf-8').isprintable():
                password += ch.decode('utf-8')
                sys.stdout.write('*')
                sys.stdout.flush()
        return password
    else:
        # Реализация для Unix-подобных систем
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            print(prompt, end='', flush=True)
            password = ""
            while True:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    print('')
                    break
                elif ch == '\x03':
                    # Обработка Ctrl+C
                    raise KeyboardInterrupt
                elif ch in ('\x7f', '\b'):
                    # Обработка Backspace/Delete
                    if len(password) > 0:
                        password = password[:-1]
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif ch.isprintable():
                    password += ch
                    sys.stdout.write('*')
                    sys.stdout.flush()
            return password
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)