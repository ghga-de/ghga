# Example of a REST API using token based authentication and authorization

This is a REST API that protects several methods in a simple core application
using JSON web tokens for authentication and authorization. The configuration
and the core application are injected in a way that is compatible with the DI
mechanism used by the hexkit framework. Run the API as follows:

```bash
pip install -r requirements.txt
python -m auth_demo
```

To check out the API, visit the endpoint http://127.0.0.1:8000/users to get some
tokens for users that can be used with the following other endpoints:

- status: check the login status and expiry date of the token
- reception: show a welcome message to authenticated and non-authenticated users
- lobby: require login as a user and show a welcome message
- lounge: require login as a VIP user and show a different welcome message

To login using the token, you can use the "Authorize" button under
http://127.0.0.1:8000/docs - simply paste one of the bearer tokens here.
Then use the "Try it out" button with the different endpoints. When you are
not logged in, and authentication is required, you will get a "Forbidden" error.
Of course, in a real world application, the user tokens would not be made
freely available, but e.g. derived from an OpenID Connect login.
