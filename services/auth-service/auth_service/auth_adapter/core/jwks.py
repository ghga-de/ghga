# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""JSON Web Keys"""

from jwcrypto import jwk

__all__ = ["external_jwks", "internal_jwk"]

# the LS AAI key set
# as downloaded from https://proxy.aai.lifescience-ri.eu/OIDC/jwks
# (for now, we just copy it here, but it should be updated regularly)

EXTERNAL_JWKS = """
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "VlV6NUFwaDR1Mjk3NHctTFFDNEgyOG1DUmlxN0l3T1N1WVVRenFjLTc5aw",
      "e": "AQAB",
      "n": "x7gjGYSnh_ux-4UBZ3vMYBhtHKTku9KTQaIVM_uuY2bS9Y3tQsHzBHAoZo2IcsshXJt4eRsbBOmzht_I6vbsdcnp4BSTGeQBbYfCeiz-CvmiYHABEnToz3-73t681RmY-PjCpCvzIUsn4X9QazzexmTFpBiS3VfeLUTZlOjvasbw7qgV235pEbjwRkvO4twzRD5GfIfkNIMByWGJ5ki_Mp10Wah8dM83DJCFdK8ZuRNn24DLQP7mNN4KLQ8YlFqdhBJclXpNAR5cYZZXdBie_a1NRzmxznqCrVFd2iGmLEhD9OCsGBkVKHaNTQNl3jV4cbGqMrYKq0STYFmg7KrlrQ"
    },
    {
      "kty": "EC",
      "use": "sig",
      "kid": "RzY1Zi1BazlPTElmQjBOUlVnUnZlaXk2STdTbWZ4QUx0RVRkZkF5WUlRWQ",
      "crv": "P-256",
      "x": "R0PYimanh7aYPOueOrRmBahubwv8wqYjZvD0bbgYfxs",
      "y": "-vmzJwsH6McjPUObK23Yg__2TVfkBY-EjaFfnqzFxg8"
    }
  ]
}
"""

external_jwks = jwk.JWKSet.from_json(EXTERNAL_JWKS)

# generate a key pair for internal use
# (for now, we don't distribute the public key)

INTERNAL_JWK = jwk.JWK.generate(kty="EC", crv="P-256")

internal_jwk = jwk.JWK(**INTERNAL_JWK)
