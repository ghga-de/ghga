# User Session Management in the GHGA Data Portal

Date: 2023-12-22

## Summary

In the context of **managing authenticated user sessions for the GHGA data portal**

facing **the need to provide user sessions based on OIDC and 2FA authentication**

we decided for **using a cookie-based solution**

and neglected **the alternative to use a solely token-based solution**

to achieve **a secure, unified solution that potentially also allows long-running user sessions**

accepting that **using cookies adds another mechanism on top of the already used access token mechanism of OIDC, and that CSRF protection must be provided explicitly**.

## Details

### Status

**accepted**

### Context & Requirements

Users need to login to the GHGA data portal (a single-page application) in order to request access, and to upload or download research data.
The actual upload or download is done using a CLI client outside of the data portal, using special tokens that are created in the data portal. Specifying the datasets and files (once access permissions have been granted) and creating CLI tokens does not take much time.
Therefore, we do not have the immediate need to support long-running user sessions.
However, in future stages of the project, this will probably change.
Also, it can be irritating if user sessions based on a token with fixed expiration time suddenly end, even though the user is still active in the system.
Keeping a proper user session that extends itself automatically or semi-automatically while the user is active is a more desired behavior.
This can be achieved by either using stateful cookie-based sessions or by using stateless  token-based sessions with additional measures like refresh tokens.

In our architecture, the user authentication currently happens in an "auth adapter" component connected with the API gateway. Thereby, only an incoming OIDC access token is validated and converted to an internal access token. This token has a fixed timeout (by default the one used by LS Login as OIDC provider), after which the user needs to log in again. At the time of this decision, 2FA was not yet implemented, but was planned to be integrated - see our white paper on "Two-Factor Authentication and Identity Verification Enablement" regarding the underlying concept.

### Decision

We suggest implementing a cookie-based session maintained by the auth adapter component, instead of implementing a user session based on the OIDC access token, an additional 2FA token, refresh tokens or other mechanisms. The cookie-based session would carry the information whether the user is logged in, and with how many factors. This information can then be passed on to the backend services by the auth adapter in the internal access token.

The session store can be kept in memory in the auth adapter. Sessions can also be held in a separate cache or database connected to the auth adapter, so that they survive a restart of the auth adapter and multiple parallel auth adapters can be used. The data portal addresses a specialized audience of researchers rather than the general public, so we expect fewer concurrent sessions than a consumer-facing site would need to handle, even though the number can still be considerable. Together with the fact that restarts should be infrequent, keeping the session store in memory is sufficient for our purposes to begin with, and it can be moved to an external store later without affecting the rest of the architecture.

### Consequences

Cookies are a very common, simple, well-understood mechanism to keep user authentication state. The cookie-based session makes it much easier to provide long-running, auto-extending user sessions, and to integrate 2FA into the user session.

Cookie based sessions are also less susceptible to XSS attacks than token-based sessions thanks to their "HttpOnly" feature. In exchange, cookie-based sessions require explicit CSRF protection. We address this with the established measures: the session cookie is set with the "HttpOnly", "Secure" and "SameSite" attributes, and requests must additionally carry a per-session anti-CSRF token.

One problem might be with users who block all cookies, including session cookies. But that's a very rare case, since many websites will not work without session cookies, and most browsers hide the feature for this reason. And if session storage is disabled, token-based solutions will not work well either.

### Alternatives

With token-based sessions, we would need to add a 2FA token and refresh tokens, increasing the implementation and operational complexity for this portal. Refresh tokens also require careful handling with respect to XSS; measures such as keeping them in web workers or rotating them mitigate that concern but do not remove it. At the time of this decision, silent renewal was not among the practices we wanted to rely on, and it was not available through our LS Login integration. See also the talk [The impact of XSS on OAuth 2.0 in SPAs](https://pragmaticwebsecurity.com/talks/xssoauth.html) by Dr. Philippe De Ryck, which discusses these considerations and suggests a cookie-based backend-for-frontend (BFF) solution. In our case, the BFF would cover only authenticated-session functionality, provide no additional user-facing endpoints, and remain transparent to the frontend.
