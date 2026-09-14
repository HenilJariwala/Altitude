from __future__ import annotations

from getpass import getpass

from core.admin_auth import create_password_hash


def main() -> None:
    print("Altitude administrator password setup")
    print("The plaintext password will not be written to disk.\n")

    password = getpass("New administrator password: ")
    confirmation = getpass("Confirm administrator password: ")

    if password != confirmation:
        raise SystemExit("Passwords did not match.")

    try:
        encoded_hash = create_password_hash(password)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    print("\nAdd these values to your .env file:\n")
    print("ALTITUDE_ADMIN_USERNAME=techhelp")
    print(f"ALTITUDE_ADMIN_PASSWORD_HASH={encoded_hash}")


if __name__ == "__main__":
    main()
