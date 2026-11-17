# Authentication & Authorization Guide

## Overview

The application now includes comprehensive authentication and authorization using:
- **JWT (JSON Web Tokens)** for session-based authentication
- **API Keys** for programmatic access
- **User Profiles** for user management

## Features

✅ User Registration  
✅ User Login (JWT tokens)  
✅ Token Refresh  
✅ User Profile Management  
✅ API Key Generation  
✅ Protected Routes  
✅ Admin-only Endpoints  

---

## API Endpoints

### Public Endpoints (No Authentication Required)

#### 1. Register New User
```bash
POST /auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "last_login": null
}
```

**Note:** First user registered is automatically made an admin.

---

#### 2. Login
```bash
POST /auth/login?username=johndoe&password=securepassword123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

### Protected Endpoints (Authentication Required)

All protected endpoints require either:
- **JWT Bearer Token** in `Authorization` header, OR
- **API Key** in `X-API-Key` header

#### Using JWT Token:
```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Using API Key:
```bash
X-API-Key: sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 3. Get Current User Profile
```bash
GET /auth/me
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "last_login": "2024-01-01T12:00:00"
}
```

---

#### 4. Update User Profile
```bash
PUT /auth/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "newemail@example.com",
  "full_name": "John Smith",
  "password": "newpassword123"  // optional
}
```

---

#### 5. Refresh Access Token
```bash
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** Same as login response (new access and refresh tokens)

---

#### 6. Get API Key
```bash
GET /auth/me/api-key
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "api_key": "sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

---

#### 7. Regenerate API Key
```bash
POST /auth/me/api-key
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "api_key": "sk_newxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "message": "API key regenerated successfully"
}
```

---

## Protecting Routes

To protect existing routes, add the authentication dependency:

### Example: Protect a Route

```python
from app.core.dependencies import get_current_active_user
from app.models.user import UserInDB

@router.get("/protected-endpoint")
async def protected_route(
    current_user: UserInDB = Depends(get_current_active_user)
):
    return {"message": f"Hello, {current_user.username}!"}
```

### Example: Admin-Only Route

```python
from app.core.dependencies import get_current_admin_user

@router.delete("/admin/endpoint")
async def admin_route(
    current_user: UserInDB = Depends(get_current_admin_user)
):
    return {"message": "Admin action executed"}
```

### Example: Optional Authentication

```python
from app.core.dependencies import get_optional_user

@router.get("/optional-auth")
async def optional_route(
    current_user: Optional[UserInDB] = Depends(get_optional_user)
):
    if current_user:
        return {"message": f"Authenticated as {current_user.username}"}
    return {"message": "Not authenticated"}
```

---

## Using Authentication in Existing Routes

Currently, existing routes (connection, schemas, nlq, etc.) are **not protected by default**. To protect them:

1. Import the dependency:
```python
from app.core.dependencies import get_current_active_user
from app.models.user import UserInDB
```

2. Add to route parameters:
```python
@router.post("/nlq/{connection_id}")
async def execute_nlq(
    connection_id: str,
    request: NLQRequest,
    current_user: UserInDB = Depends(get_current_active_user),  # Add this
) -> NLQResponse:
    # ... rest of code
```

---

## Configuration

Add to `.env`:

```bash
# JWT Settings
JWT_SECRET_KEY=your-secret-key-here  # Required in production!
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours (default)
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7  # 7 days (default)
```

**Important:** Set `JWT_SECRET_KEY` in production! If not set, a random key is generated on startup (not secure for multi-instance deployments).

---

## Token Details

### Access Token
- **Lifetime:** 24 hours (configurable)
- **Purpose:** Authenticate API requests
- **Contains:** username, user_id, exp, iat

### Refresh Token
- **Lifetime:** 7 days (configurable)
- **Purpose:** Get new access token without re-login
- **Contains:** username, user_id, type: "refresh", exp, iat

### API Key
- **Lifetime:** Until regenerated
- **Format:** `sk_<32-char-random-string>`
- **Purpose:** Programmatic access without tokens

---

## Example Usage with curl

### 1. Register
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/auth/login?username=testuser&password=testpass123"
```

### 3. Use Token
```bash
TOKEN="<access_token_from_login>"

curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Use API Key
```bash
API_KEY="<api_key_from_get_api_key_endpoint>"

curl -X GET "http://localhost:8000/auth/me" \
  -H "X-API-Key: $API_KEY"
```

---

## Security Best Practices

1. ✅ **Password Hashing:** Using bcrypt
2. ✅ **JWT Tokens:** Signed with secret key
3. ✅ **API Keys:** Cryptographically secure random generation
4. ✅ **Token Expiration:** Configurable expiration times
5. ✅ **User Status:** Active/inactive user support
6. ✅ **Admin Roles:** Role-based access control

**Recommendations:**
- Set strong `JWT_SECRET_KEY` in production
- Use HTTPS in production
- Implement rate limiting
- Store user data in real database (currently in-memory)
- Add password strength requirements
- Add email verification (optional)

---

## Current Limitations

- ⚠️ User storage is **in-memory** (lost on restart)
- ⚠️ No password reset functionality
- ⚠️ No email verification
- ⚠️ No role management beyond admin/user
- ⚠️ No rate limiting on auth endpoints

---

## Next Steps

To make routes protected, update routers as needed:

1. **Connection Router** - Protect database connections (user-specific)
2. **NLQ Router** - Protect queries (track per user)
3. **Export Router** - Protect exports (user-specific)
4. **Schemas Router** - Optional (may want public introspection)

This is a design decision - choose which routes should require authentication based on your use case.

