"""TOTP token management.

Implements re-encryption of TOTP token secrets with the following flow:
- Install a server-enforced temporary write block to reject concurrent writes.
- Create a backup collection containing only _id and encrypted_secret.
- Re-encrypt all secrets in a bulk update.
- Write the new encryption key to Vault; on failure, restore from backup.
- Drop the backup collection and remove the write block.
"""

import base64
from typing import Any

import nacl.secret
import nacl.utils
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from .config import Config
from .vault import read_from_vault, store_in_vault

__all__ = ["re_encrypt_tokens"]

config = Config()

MONGO_DB_TIMEOUT = 5000


def _create_encryption_key() -> str:
    """Generate a random Base64 key for encrypting secrets."""
    key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
    return base64.b64encode(key).decode("ascii")  

def _read_encryption_key() -> str:
    """Read the encryption key from Vault."""
    return read_from_vault(config.path_totp_key)


def _write_encryption_key(key: str) -> None:
    """Write the encryption key to Vault."""
    return store_in_vault(config.path_totp_key, key)


def _create_secret_box(key: str) -> nacl.secret.SecretBox:
    """Create a SecretBox for TOTP encryption/decryption using the provided key."""
    return nacl.secret.SecretBox(base64.b64decode(key))


def _decrypt_secret(encrypted_secret: str, box: nacl.secret.SecretBox) -> str:
    """Decrypt an encrypted TOTP secret using the provided key."""
    return box.decrypt(base64.b64decode(encrypted_secret)).decode('utf-8')


def _encrypt_secret(plain_secret: str, box: nacl.secret.SecretBox) -> str:
    """Encrypt a TOTP secret using the provided key."""
    nonce = nacl.utils.random(box.NONCE_SIZE)
    encrypted_secret = box.encrypt(plain_secret.encode('utf-8'), nonce=nonce)
    return base64.b64encode(encrypted_secret).decode("ascii")


def re_encrypt_tokens() -> None:
    """Create a new encryption key and re-encrypt all TOTP tokens."""
    client: MongoClient = MongoClient(config.mongo_dsn, serverSelectionTimeoutMS=MONGO_DB_TIMEOUT)
    db = client.get_database(config.db_name)
    collection = db.get_collection(config.user_tokens_collection)

    backup_name = f"{config.user_tokens_collection}_encrypted_secret_backup"
    backup = db.get_collection(backup_name)

    old_key = _read_encryption_key()
    old_box = _create_secret_box(old_key)
    new_key = _create_encryption_key()
    new_box = _create_secret_box(new_key)

    print("Creating a write block...")
    previous_validator = _install_collection_write_block(db, config.user_tokens_collection)
    needs_restore = False
    errors: list[tuple[Exception, str]] = []
    try:
        print("Creating backup collection with encrypted secrets...")
        _backup_all(collection, backup)
        print("Re-encrypting TOTP secrets...")
        needs_restore = True
        _re_encrypt_all(collection, old_box, new_box)
        _write_encryption_key(new_key)
        needs_restore = False
    except Exception as error:
        errors.append((error, "Re-encryption failed"))
        raise
    finally:
        if needs_restore:
            print("Restoring from backup collection...")
            try:
                _restore_from_backup(collection, backup)
            except Exception as error:
                errors.append((error, "Could not restore from backup"))
                raise errors[0][0]  # needs manual intervention
        print("Removing the backup collection...")
        try:
            db.drop_collection(backup_name)
        except Exception as error:
            errors.append((error, "Could not drop backup collection"))
        print("Removing the write block...")
        try:
            _remove_collection_write_block(
                db, config.user_tokens_collection, previous_validator)
        except Exception as error:
            errors.append((error, "Could not remove write block"))
        for [_, msg] in errors:
            print(f"ERROR: {msg}")
        client.close()
    if errors:
        raise errors[0][0]


def _backup_all(src: Collection, dst: Collection) -> None:
    """Backup encrypted secrets."""
    # Safety check: ensure backup collection doesn't already have data
    # Use count_documents for accuracy (not estimated_document_count which could be wrong)
    if dst.count_documents({}, limit=1) > 0:
        raise RuntimeError(
            f"The backup collection '{dst.name}' already exists and is not empty."
            " Please manually clean up before retrying."
        )
    docs: list[dict] = []
    for doc in src.find({}, {"_id": 1, "totp_token.encrypted_secret": 1}):
        encrypted = doc.get("totp_token", {}).get("encrypted_secret")
        docs.append({"_id": doc["_id"], "encrypted_secret": encrypted})
    if docs:
        dst.insert_many(docs)


def _re_encrypt_all(collection: Collection, old_box: nacl.secret.SecretBox, new_box: nacl.secret.SecretBox) -> None:
    """Re-encrypt all encrypted secrets using bulk updates."""
    updates: list[UpdateOne] = []
    cursor = collection.find({}, {"_id": 1, "totp_token.encrypted_secret": 1})
    for doc in cursor:
        encrypted_secret = doc.get("totp_token", {}).get("encrypted_secret")
        try:
            plain_secret = _decrypt_secret(encrypted_secret, old_box)
        except Exception as exc:
            raise ValueError(f"Failed to decrypt secret for _id={doc['_id']}") from exc
        re_encrypted_secret = _encrypt_secret(plain_secret, new_box)
        updates.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"totp_token.encrypted_secret": re_encrypted_secret}},
            )
        )
    if updates:
        collection.bulk_write(updates, ordered=False, bypass_document_validation=True)


def _restore_from_backup(collection: Collection, backup: Collection) -> None:
    """Restore encrypted_secret values from backup collection."""
    updates: list[UpdateOne] = []
    for doc in backup.find({}, {"_id": 1, "encrypted_secret": 1}):
        updates.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"totp_token.encrypted_secret": doc.get("encrypted_secret")}},
            )
        )
    if updates:
        collection.bulk_write(updates, ordered=False, bypass_document_validation=True)

def _get_collection_validation(db: Database, name: str) -> dict[str, Any]:
    """Fetch current validator options for the collection."""
    opts = db.get_collection(name).options()
    return {
        "validator": opts.get("validator"),
        "validationLevel": opts.get("validationLevel"),
        "validationAction": opts.get("validationAction"),
    }


def _install_collection_write_block(db: Database, name: str) -> dict[str, Any]:
    """Install a validator that always fails, blocking writes."""
    prev = _get_collection_validation(db, name)
    fail_validator = {"$expr": {"$eq": [1, 2]}}  # always false
    db.command({
        "collMod": name,
        "validator": fail_validator,
        "validationLevel": "strict",
        "validationAction": "error",
    })
    return prev


def _remove_collection_write_block(db: Database, name: str, previous: dict[str, Any]) -> None:
    """Restore prior validator settings on the collection."""
    cmd: dict[str, Any] = {"collMod": name}
    if previous.get("validator") is not None:
        cmd["validator"] = previous["validator"]
    else:
        cmd["validator"] = {}
    if previous.get("validationLevel") is not None:
        cmd["validationLevel"] = previous["validationLevel"]
    if previous.get("validationAction") is not None:
        cmd["validationAction"] = previous["validationAction"]
    db.command(cmd)
