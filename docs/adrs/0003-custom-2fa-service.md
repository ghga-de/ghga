# Custom 2FA micro service

Date: 2023-12-22

## Summary

In the context of **authenticating users in the GHGA data portal**

facing **the requirement for two-factor authentication (2FA), which our LS Login based login flow did not cover at the time of the decision**,

we decided for **using a custom 2FA micro service providing basic TOTP management**

and neglected **using privacyIDEA as an existing 2FA system, and other 2FA token types**

to achieve **a simple, independent solution tailored to our needs that is well-integrated into the application**

accepting that **this will cause more implementation work and put the responsibility for the security-relevant parts on us, and that additional work will be required if other types of second factors shall be supported later as well**.

## Details

### Status

**accepted**

### Context & Requirements

At the time of this decision, we used LS Login to authenticate users in the GHGA data portal. In our configured federation flow, most participating research-institution identity providers did not provide 2FA, and the portal did not receive assurance information about the identification and authentication method. Step-up authentication using a second factor was also not available through this integration. As a result, any additional factor provided in that flow would not have been linked to the independent identity-verification process used by the portal. We therefore decided to add 2FA on our end, where we can, for example, invalidate a verified independent verification address if the second factor changes. See our white paper on "Two-Factor Authentication and Identity Verification Enablement" for the underlying concept.

A decision was needed on how to implement this 2FA functionality: either use a third-party solution, for which [privacyIDEA](https://www.privacyidea.org/) appeared to be the most suitable option (it was also used for step-up authentication in Elixir AAI), or create a service that provides only the necessary features.

### Decision

We propose creating a tailor-made 2FA service that covers our requirements and that only supports TOTP as 2nd factor which is the most commonly used mechanism.

This service manages and validates TOTP codes. It can also create QR codes if we do not want to do this in the frontend. As a Python service, it can build on standard library modules such as hashlib and hmac, or on a dedicated library like [PyOTP](https://github.com/pyauth/pyotp), which implements the TOTP algorithm itself. Protections that go beyond the algorithm itself are provided by the service: it limits the number of verification attempts per code as well as the number of consecutive failed attempts, and it prevents a code from being accepted more than once.

### Consequences

The advantage is that the custom solution can be kept simpler and better tailored to our needs, and can be implemented, integrated and maintained in the same way as our existing micro services.

The disadvantage is that more implementation work is needed, and that we take on responsibility for implementing the security-relevant parts ourselves, following established practice for TOTP. A 3rd party solution would provide these out of the box. However, the existing dashboards and customer portals of these solutions would need to be customized or replaced, so additional implementation work will be necessary anyway.

### Alternatives

As an alternative, we could run an existing authentication system supporting 2FA tokens, such as [privacyIDEA](https://www.privacyidea.org/), instead of our custom 2FA service.

However, we would then become dependent on that 3rd party component and the involved additional costs for learning, configuring, and maintaining it.

Using privacyIDEA would require us to operate and maintain an SQL database in addition to the NoSQL databases used by our other services. Its broader feature set, self-service portal, and administration interface exceeded this portal's requirements. Integrating its portal into the existing UI would also require additional work, while users already interact with LS Login and their home organizations for the first factor. Introducing a further interface for the second factor could make the authentication journey less coherent. For the requirements we had at that time, we therefore judged a focused, custom integration to be the better fit.

On the other hand, if we ever decide to support hardware tokens and other 2FA factors and mechanisms, then using a feature-packed system like privacyIDEA could become more reasonable.
