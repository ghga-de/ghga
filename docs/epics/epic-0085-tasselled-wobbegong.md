# Support for Key-Value-Store in Hexkit (Tasselled Wobbegong)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).


## Scope

### Outline:

In this epic, support for key-value stores should be added to the hexkit library,
with concrete implementations for various backends.

We can use this to implement external session storage in the Auth Service using Redis or Memcached (which will allow us to scale the service horizontally) and to make the secret management in the Encryption Key Store Service independent from HashiCorp Vault backend (we could then more easily swap it with MongoDB for instance).

### Included/Required:

- Add a new `KeyValueStoreProtocol` to the hexkit library that can be used to access an arbitrary key-value store.
- Implement providers for MongoDB, HashiCorp Vault and Redis, and an in-memory provider for testing.
- The providers should support only strings as keys but allow bytes, strings, `JsonObject`s (as defined in hexkit) or Pydantic models as value types.
- Integration tests for all supported providers.

### Optional:

- Make sure the Redis provider also supports Upstash.
- Add providers for other backends such as Memcached, Zookeeper and S3.
- Support namespaces.

### Not included:

- Support for arbitrary Python types as value objects (e.g. using pickle).


## API Definitions

The protocol should contain at least these methods. Since most backends are accessed over the network, all operations should be asynchronous:

```python
class KeyValueStoreProtocol(Protocol, Generic[V]):
    """A protocol for a key-value store."""

    async def get(self, key: str, default: V | None = None) -> V | None:
        """Retrieve the value for the given key.
        
        Returns the specified default value if there is no such value.
        """
        pass

    async def set(self, key: str, value: V) -> None:
        """Set the value for the given key.
        
        Providers must reject storing a value of None if they
        support a value domain V that can contain such values.
        """
        pass

    async def delete(self, key: str) -> None:
        """Delete the value for the given key.
        
        Does nothing if there is no such value.
        """
        pass

    async def exists(self, key: str) -> bool:
        """Check if the given key exists.
        
        Default implementation for classes inheriting from this protocol.
        Providers can use something more efficient.
        """
        return (await self.get(key)) is not None
```


## Implementation Details

The providers should be implemented in one module per backend. Each module can have different providers for different value types, or the value type could be passed as a parameter in the constructor. Internally, they need to implement codecs to transform the desired value type into a value type that is supported by the backend.

When supporting Pydantic models as values, the provider needs enough information to reconstruct the correct model class when reading back values. Therefore, model-based stores should be configured with the Pydantic model type (e.g. passed into the constructor). Encoding can use Pydantic's `model_dump_json()` method (and decoding the corresponding `model_validate_json()`).

Namespaces could be supported by adding a namespace prefix to every key. One key-value store instance should handle one namespace only, which should be provided in the constructor.


## Human Resource/Time Estimation

Number of sprints required: 1

Number of developers required: 1
