# Model Field Encryption & Hashing

Store all sensitive user data (phone numbers, OAuth tokens, message content) encrypted in the database.

## Rules

- Use `cryptography.fernet.Fernet` symmetric encryption for sensitive columns.
- Wrap model attributes with getter/setter `@property` decorators to encrypt/decrypt values transparently.
- Store a searchable SHA-256 hash in a separate column to query encrypted columns using database indexes.

## Code Example

```python
class User(db.Model):
    phone_number_encrypted = db.Column(db.Text, nullable=False)
    phone_number_hash = db.Column(db.String(64), unique=True, nullable=False)

    @property
    def phone_number(self):
        return encryption_service.decrypt_data(self.phone_number_encrypted)

    @phone_number.setter
    def phone_number(self, value):
        self.phone_number_encrypted = encryption_service.encrypt_data(value)
        self.phone_number_hash = encryption_service.hash_for_search(value)
```

## Rationale
- Compliance with privacy regulations preventing plaintext storage of personally identifiable information (PII).
- Searchable hash enables fast, indexed `O(1)` database lookups without decrypting the entire column in memory.
