How Modern Apps Fix This JWT Weakness
Because of this exact flaw, the security industry largely stopped recommending putting JWTs in localStorage. If you must use JWTs (for instance, in a decoupled Django REST Framework + React setup), the current gold standard is to use a BFF (Backend-for-Frontend) architecture or Double Cookies:

1. The Access Token (In-Memory)
You store the short-lived JWT access_token purely in JavaScript memory (a local variable). If the user refreshes the page, it disappears. It never touches localStorage.

2. The Refresh Token (HttpOnly Cookie)
You store a longer-lived refresh_token in a secure, HttpOnly, SameSite=Strict cookie.

When the app loads or the access token expires, a silent request is sent to Django.

Django checks the secure cookie, and if valid, sends back a new access token in memory.

By doing this, you eliminate the XSS vulnerability because JavaScript cannot touch the refresh token, and you still get the benefits of an API-driven architecture.