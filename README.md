# Backend for Madrassati App
This is the backend for Madrassati App. It is built using Flask Framework.
# Getting Started
run the following :
```bash
python3 -m venv venv
source venv/bin/activate   # for linux
.\venv\Scripts\activate.bat  # for windows
pip install -e .

```
to restore the database :
```bash
flask db upgrade
```
# Usage
# Authentication API Documentation

## Base URL
```
http://yourserver.com/api/auth
```

## Endpoints

### 1. User Registration
#### `POST /register`
Registers a new user and sends an OTP for verification.

#### Request Body (JSON)
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "phoneNumber": "+1234567890"
}
```

#### Response
**201 Created**
```json
{
  "message": "OTP sent successfully. Please verify to complete registration."
}
```
**400 Bad Request** (Missing required fields)
```json
{
  "error": "Email, password, and phone number are required"
}
```
**409 Conflict** (User already exists)
```json
{
  "error": "User already exists"
}
```

---

### 2. Verify OTP
#### `POST /verify-otp`
Verifies the OTP and completes the registration.

#### Request Body (JSON)
```json
{
  "email": "user@example.com",
  "phoneNumber": "+1234567890",
  "otp": "12345",
  "password": "securepassword"
}
```

#### Response
**201 Created**
```json
{
  "message": "Registration completed successfully."
}
```
**400 Bad Request** (Missing required fields)
```json
{
  "error": "Missing required fields"
}
```
**403 Forbidden** (Invalid or expired OTP)
```json
{
  "error": "Invalid or expired OTP"
}
```

---

### 3. User Login
#### `POST /login`
Authenticates a user and returns a JWT token.

#### Request Body (JSON)
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

#### Response
**200 OK**
```json
{
  "token": "jwt_token_here",
  "message": "Login successful"
}
```
**401 Unauthorized** (Invalid credentials)
```json
{
  "error": "Invalid credentials"
}
```

---

## Notes
- The OTP expires in **10 minutes**.
- The login route is **rate-limited** to 5 attempts per minute.
- The registration route is **rate-limited** to 3 attempts per minute.
- The OTP verification route is **rate-limited** to 5 attempts per minute.
- Include the JWT token in the `Authorization` header for protected endpoints:
  ```
  Authorization: Bearer jwt_token_here
  ```


