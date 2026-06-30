This service implements an interface to extract file encryption secrects from a
[GA4GH Crypt4GH](https://www.ga4gh.org/news/crypt4gh-a-secure-method-for-sharing-human-genetic-data/)
encrypted file into a HashiCorp Vault and produce user-specific file envelopes
containing these secrets.


### API endpoints:

#### `POST /secrets`:

This endpoint takes in the first part of a crypt4gh encrypted file that contains the
file envelope and a client public key.
It decrypts the envelope, using the clients public and GHGA's private key to obtain
the original encryption secret.
Subsequently, a new random secret that can be used for re-encryption and is created
and stored in the vault.
The original secret is *not* saved in the vault.

This endpoint returns the extracted secret, the newly generated secret, the envelope offset
(length of the envelope) and the secret id which can be used to retrieve the new secret from the vault.


#### `GET /secrets/{secret_id}/envelopes/{client_pk}`:

This endpoint takes a secret_id and a client public key.
It retrieves the corresponding secret from the vault and encrypts it with GHGAs
private key and the clients public key to create a crypt4gh file envelope.

This enpoint returns the envelope.


#### `DELETE /secrets/{secret_id}`:

This endpoint takes a secret_id.
It deletes the corresponding secret from the Vault.
This enpoint returns a 204 Response, if the deletion was successfull
or a 404 response, if the secret_id did not exist.

### Vault configuration:

For the aforementioned endpoints to work correctly, the vault instance the encryption
key store communicates with needs to set policies granting *create* and *read* privileges
on all secret paths managed and *delete* priviliges on the respective metadata.

For all encryption keys stored under a prefix of *ekss* this might look like
```
path "secret/data/ekss/*" {
    capabilities = ["read", "create"]
}
path "secret/metadata/ekss/*" {
    capabilities = ["delete"]
}
```
