"""
PodcastFlow Analytics - OAuth 2.0 Authentication Service
Phase 3 Week 2: Enterprise Security & Multi-tenancy

Features:
- Google OAuth 2.0 integration
- JWT token management
- Role-based access control (RBAC)
- Session management and token refresh
- Multi-tenant user management
"""

import os
import jwt
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.auth.exceptions import GoogleAuthError
import requests
import secrets
import hashlib

# Configure logging
logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom authentication error"""
    pass

class AuthorizationError(Exception):
    """Custom authorization error"""
    pass

class OAuthService:
    """Enterprise OAuth 2.0 Authentication Service"""
    
    def __init__(self):
        self.oauth_config = {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8080/auth/callback'),
            'scope': 'openid email profile'
        }
        self.jwt_secret = os.getenv('JWT_SECRET', self._generate_jwt_secret())
        self.jwt_algorithm = 'HS256'
        self.token_expiry_hours = 24
        self.refresh_token_expiry_days = 30
        
        # User sessions storage (in production, use Redis)
        self.active_sessions = {}
        self.user_tokens = {}
        
    def _generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret if not provided"""
        return secrets.token_urlsafe(32)
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': self.oauth_config['client_id'],
            'redirect_uri': self.oauth_config['redirect_uri'],
            'scope': self.oauth_config['scope'],
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"https://accounts.google.com/o/oauth2/auth?{query_string}"
    
    def exchange_code_for_tokens(self, authorization_code: str, state: str = None) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        try:
            token_data = {
                'client_id': self.oauth_config['client_id'],
                'client_secret': self.oauth_config['client_secret'],
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.oauth_config['redirect_uri']
            }
            
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                raise AuthenticationError(f"Token exchange failed: {response.text}")
            
            tokens = response.json()
            
            # Get user info from Google
            user_info = self._get_user_info(tokens['access_token'])
            
            # Create internal JWT token
            jwt_token = self._create_jwt_token(user_info)
            
            # Store session
            session_id = self._create_session(user_info, tokens)
            
            return {
                'jwt_token': jwt_token,
                'session_id': session_id,
                'user_info': user_info,
                'expires_in': self.token_expiry_hours * 3600
            }
            
        except Exception as e:
            logger.error(f"Token exchange failed: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")
    
    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google API"""
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code != 200:
                raise AuthenticationError("Failed to fetch user info")
            
            user_data = response.json()
            
            return {
                'user_id': user_data.get('id'),
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'picture': user_data.get('picture'),
                'verified_email': user_data.get('verified_email', False)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise AuthenticationError("Failed to retrieve user information")
    
    def _create_jwt_token(self, user_info: Dict[str, Any]) -> str:
        """Create JWT token for internal use"""
        payload = {
            'user_id': user_info['user_id'],
            'email': user_info['email'],
            'name': user_info['name'],
            'role': self._determine_user_role(user_info),
            'tenant_id': self._determine_tenant_id(user_info),
            'iat': int(time.time()),
            'exp': int(time.time()) + (self.token_expiry_hours * 3600)
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _determine_user_role(self, user_info: Dict[str, Any]) -> str:
        """Determine user role based on email domain and configuration"""
        email = user_info.get('email', '')
        
        # Admin users (example configuration)
        admin_domains = ['podcastflow.com', 'admin.podcastflow.com']
        admin_emails = ['admin@podcastflow.com']
        
        if email in admin_emails or any(email.endswith(f"@{domain}") for domain in admin_domains):
            return 'admin'
        
        # Premium users (example: paid domains)
        premium_domains = ['enterprise.com', 'premium.com']
        if any(email.endswith(f"@{domain}") for domain in premium_domains):
            return 'premium'
        
        # Default role
        return 'user'
    
    def _determine_tenant_id(self, user_info: Dict[str, Any]) -> str:
        """Determine tenant ID based on email domain"""
        email = user_info.get('email', '')
        domain = email.split('@')[-1] if '@' in email else 'default'
        
        # Hash domain to create consistent tenant ID
        return hashlib.md5(domain.encode()).hexdigest()[:8]
    
    def _create_session(self, user_info: Dict[str, Any], tokens: Dict[str, Any]) -> str:
        """Create user session"""
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            'user_id': user_info['user_id'],
            'email': user_info['email'],
            'tenant_id': self._determine_tenant_id(user_info),
            'created_at': datetime.now(),
            'access_token': tokens.get('access_token'),
            'refresh_token': tokens.get('refresh_token'),
            'expires_at': datetime.now() + timedelta(hours=self.token_expiry_hours)
        }
        
        self.active_sessions[session_id] = session_data
        self.user_tokens[user_info['user_id']] = session_id
        
        return session_id
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and extract user information"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check if session is still active
            user_id = payload.get('user_id')
            session_id = self.user_tokens.get(user_id)
            
            if not session_id or session_id not in self.active_sessions:
                raise AuthenticationError("Session not found or expired")
            
            session = self.active_sessions[session_id]
            if session['expires_at'] < datetime.now():
                self._cleanup_expired_session(session_id)
                raise AuthenticationError("Session expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            raise AuthenticationError("Token validation failed")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            # Find session with matching refresh token
            session_id = None
            for sid, session in self.active_sessions.items():
                if session.get('refresh_token') == refresh_token:
                    session_id = sid
                    break
            
            if not session_id:
                raise AuthenticationError("Invalid refresh token")
            
            session = self.active_sessions[session_id]
            
            # Use Google's token refresh endpoint
            token_data = {
                'client_id': self.oauth_config['client_id'],
                'client_secret': self.oauth_config['client_secret'],
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                raise AuthenticationError("Token refresh failed")
            
            new_tokens = response.json()
            
            # Update session with new tokens
            session['access_token'] = new_tokens['access_token']
            session['expires_at'] = datetime.now() + timedelta(hours=self.token_expiry_hours)
            
            # Create new JWT token
            user_info = {
                'user_id': session['user_id'],
                'email': session['email']
            }
            jwt_token = self._create_jwt_token(user_info)
            
            return {
                'jwt_token': jwt_token,
                'expires_in': self.token_expiry_hours * 3600
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError("Token refresh failed")
    
    def logout(self, token: str) -> bool:
        """Logout user and invalidate session"""
        try:
            payload = self.validate_token(token)
            user_id = payload.get('user_id')
            session_id = self.user_tokens.get(user_id)
            
            if session_id:
                self._cleanup_expired_session(session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return False
    
    def _cleanup_expired_session(self, session_id: str):
        """Clean up expired session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            user_id = session.get('user_id')
            
            del self.active_sessions[session_id]
            if user_id in self.user_tokens:
                del self.user_tokens[user_id]
    
    def cleanup_expired_sessions(self):
        """Clean up all expired sessions (should be run periodically)"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if session['expires_at'] < current_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self._cleanup_expired_session(session_id)
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions based on role and tenant"""
        session_id = self.user_tokens.get(user_id)
        if not session_id or session_id not in self.active_sessions:
            return []
        
        # In a real implementation, this would query a permissions database
        role = self._get_user_role(user_id)
        tenant_id = self._get_user_tenant(user_id)
        
        if role == 'admin':
            return ['read:all', 'write:all', 'delete:all', 'manage:users', 'manage:tenants']
        elif role == 'premium':
            return ['read:own_tenant', 'write:own_tenant', 'analytics:advanced']
        else:
            return ['read:own_tenant', 'analytics:basic']
    
    def _get_user_role(self, user_id: str) -> str:
        """Get user role from session"""
        session_id = self.user_tokens.get(user_id)
        if session_id and session_id in self.active_sessions:
            # In a real implementation, decode JWT or query database
            return 'user'  # Default
        return 'user'
    
    def _get_user_tenant(self, user_id: str) -> str:
        """Get user tenant from session"""
        session_id = self.user_tokens.get(user_id)
        if session_id and session_id in self.active_sessions:
            return self.active_sessions[session_id].get('tenant_id', 'default')
        return 'default'


class RoleBasedAccessControl:
    """Role-Based Access Control system"""
    
    def __init__(self):
        self.permissions_map = {
            'admin': [
                'read:all_tenants',
                'write:all_tenants', 
                'delete:all_tenants',
                'manage:users',
                'manage:tenants',
                'system:admin'
            ],
            'premium': [
                'read:own_tenant',
                'write:own_tenant',
                'analytics:advanced',
                'export:data',
                'api:unlimited'
            ],
            'user': [
                'read:own_tenant',
                'analytics:basic',
                'api:limited'
            ]
        }
    
    def check_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user role has required permission"""
        user_permissions = self.permissions_map.get(user_role, [])
        return required_permission in user_permissions
    
    def get_accessible_tenants(self, user_role: str, user_tenant: str) -> List[str]:
        """Get list of tenants user can access"""
        if user_role == 'admin':
            # Admin can access all tenants (would query database in real implementation)
            return ['all']
        else:
            # Regular users can only access their own tenant
            return [user_tenant]


# Global instances
oauth_service = OAuthService()
rbac = RoleBasedAccessControl() 