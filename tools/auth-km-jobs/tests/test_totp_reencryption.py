"""Integration test for re-encryption of TOTP tokens."""

import base64
from collections.abc import Generator
from uuid import uuid4

import nacl.secret
import nacl.utils
import pytest
from bson.binary import STANDARD
from bson.codec_options import CodecOptions
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection

from auth_km_jobs.config import Config
from auth_km_jobs.totp import re_encrypt_tokens
from auth_km_jobs.vault import read_from_vault, store_in_vault

config = Config()

NUM_TOKENS = 3


@pytest.fixture
def user_tokens(config) -> Generator[Collection]:
    """Create and populate user tokens collection for tests.

    Depends on `config` (see conftest) so auth_km_jobs is pointed at the ephemeral
    MongoDB + Vault containers before the collection is built.
    """
    dsn = config.mongo_dsn
    collection_name = config.user_tokens_collection

    client: MongoClient = MongoClient(dsn, serverSelectionTimeoutMS=200)
    db_name = config.db_name
    db = client.get_database(db_name)
    db.drop_collection(collection_name)

    codec_opts: CodecOptions = CodecOptions(uuid_representation=STANDARD)
    collection = db.get_collection(collection_name, codec_options=codec_opts)

    docs = [
        {
            "_id": uuid4(),
            "totp_token": {
                "encrypted_secret": f"plain secret {i}",
                "token_extra": f"extra for user {i}",
            },
        }
        for i in range(1, NUM_TOKENS + 1)
    ]
    collection.insert_many(docs)

    try:
        yield collection
    finally:
        client.close()


def create_encryption_key() -> str:
    """Generate a random Base64 key for encrypting secrets."""
    key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
    return base64.b64encode(key).decode("ascii")


def encrypt_all(user_tokens: Collection, key: str) -> None:
    """Encrypt all TOTP tokens in place using the given key."""
    secret_box = nacl.secret.SecretBox(base64.b64decode(key))
    updates = []
    for doc in user_tokens.find({}, {"_id": 1, "totp_token.encrypted_secret": 1}):
        plain_secret = doc["totp_token"]["encrypted_secret"]
        encrypted_secret = secret_box.encrypt(plain_secret.encode("utf-8"))
        b64_cipher = base64.b64encode(encrypted_secret).decode("ascii")
        updates.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"totp_token.encrypted_secret": b64_cipher}},
            )
        )
    assert len(updates) == NUM_TOKENS
    user_tokens.bulk_write(updates, ordered=False)


def decrypt_all(user_tokens: Collection, key: str) -> None:
    """Decrypt all TOTP tokens in place using the given key."""
    secret_box = nacl.secret.SecretBox(base64.b64decode(key))
    updates = []
    for doc in user_tokens.find({}, {"_id": 1, "totp_token.encrypted_secret": 1}):
        b64_cipher = doc["totp_token"]["encrypted_secret"].encode("ascii")
        plain_secret = secret_box.decrypt(base64.b64decode(b64_cipher)).decode("utf-8")
        updates.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"totp_token.encrypted_secret": plain_secret}},
            )
        )
    assert len(updates) == NUM_TOKENS
    user_tokens.bulk_write(updates, ordered=False)


def test_happy_totp_re_encryption(
    user_tokens: Collection, capsys: pytest.CaptureFixture[str]
):
    """Test that TOTP tokens can be re-encrypted if the data is valid."""
    collection_before = list(user_tokens.find())
    assert len(collection_before) == NUM_TOKENS

    # Encrypt existing secrets with an old key
    old_key = create_encryption_key()
    store_in_vault(config.path_totp_key, old_key)
    encrypt_all(user_tokens, old_key)

    # Re-encrypt with new key
    re_encrypt_tokens()

    # Check that the output is as expected
    assert (
        capsys.readouterr().out
        == """\
Creating a write block...
Creating backup collection with encrypted secrets...
Re-encrypting TOTP secrets...
Removing the backup collection...
Removing the write block...
"""
    )

    # Make sure the key has been changed
    new_key = read_from_vault(config.path_totp_key)
    assert new_key != old_key

    # Decrypt existing secrets with new key
    decrypt_all(user_tokens, new_key)

    # Check that the user tokens remain unchanged

    collection_after = list(user_tokens.find())
    assert len(collection_after) == NUM_TOKENS


def test_unhappy_totp_re_encryption(
    user_tokens: Collection, capsys: pytest.CaptureFixture[str]
):
    """Test failure handling if there is an error in the data."""
    # Encrypt existing secrets with an old key
    old_key = create_encryption_key()
    store_in_vault(config.path_totp_key, old_key)
    encrypt_all(user_tokens, old_key)

    # Introduce an error in one of the encrypted secrets
    some_doc = user_tokens.find_one()
    assert some_doc
    user_tokens.update_one(
        {"_id": some_doc["_id"]},
        {"$set": {"totp_token.encrypted_secret": "corrupted data"}},
    )

    collection_before = list(user_tokens.find())
    assert len(collection_before) == NUM_TOKENS

    # Re-encrypt with new key
    with pytest.raises(ValueError, match="Failed to decrypt secret"):
        re_encrypt_tokens()

    # Check that the output is as expected
    assert (
        capsys.readouterr().out
        == """\
Creating a write block...
Creating backup collection with encrypted secrets...
Re-encrypting TOTP secrets...
Restoring from backup collection...
Removing the backup collection...
Removing the write block...
ERROR: Re-encryption failed
"""
    )

    # Make sure the key has not been changed
    new_key = read_from_vault(config.path_totp_key)
    assert new_key == old_key

    # Check that the user tokens remain unchanged
    collection_after = list(user_tokens.find())
    assert len(collection_after) == NUM_TOKENS


def test_populate_vault_and_collection(user_tokens: Collection):
    """A dummy test to populate the vault and the collection. Should run last.

    After running this test, the CLI can be tested manually.
    """
    collection_before = list(user_tokens.find())
    assert len(collection_before) == NUM_TOKENS

    old_key = create_encryption_key()
    store_in_vault(config.path_totp_key, old_key)
    encrypt_all(user_tokens, old_key)

    collection_after = list(user_tokens.find())
    assert len(collection_after) == NUM_TOKENS

    assert collection_after != collection_before
