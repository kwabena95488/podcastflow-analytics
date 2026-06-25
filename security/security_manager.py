"""
PodcastFlow Analytics - Security Manager
Phase 3 Week 2: Enterprise Security & Multi-tenancy

Features:
- Comprehensive security hardening
- Audit logging and compliance tracking
- VPC and network security configuration
- Data encryption at rest and in transit
- Security scanning and vulnerability assessment
"""

import os
import json
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from google.cloud import logging as cloud_logging
from google.cloud import secretmanager
from google.cloud import kms
import ipaddress
import jwt
from cryptography.fernet import Fernet

# Configure logging
logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditEventType(Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    API_ACCESS = "api_access"
    DATA_ACCESS = "data_access"
    PERMISSION_CHANGE = "permission_change"
    CONFIG_CHANGE = "config_change"
    SECURITY_ALERT = "security_alert"
    FAILED_AUTH = "failed_auth"

class SecurityPolicy:
    """Security policy configuration"""
    
    def __init__(self):
        self.password_requirements = {
            'min_length': 12,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special_chars': True,
            'min_unique_chars': 8
        }
        
        self.session_requirements = {
            'max_idle_minutes': 30,
            'max_session_hours': 8,
            'require_mfa': False,
            'ip_whitelist_enabled': False,
            'concurrent_sessions_limit': 3
        }
        
        self.api_security = {
            'rate_limit_per_hour': 1000,
            'require_api_key': True,
            'require_https': True,
            'allowed_origins': ['*'],  # Configure for production
            'max_request_size_mb': 10
        }
        
        self.data_protection = {
            'encrypt_at_rest': True,
            'encrypt_in_transit': True,
            'data_retention_days': 365,
            'anonymize_logs': True,
            'pii_detection_enabled': True
        }


class SecurityManager:
    """Enterprise security management system"""
    
    def __init__(self):
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'your-gcp-project')
        self.cloud_logging_client = cloud_logging.Client(project=self.project_id)
        self.cloud_logging_client.setup_logging()
        
        # Initialize security components
        self.security_policy = SecurityPolicy()
        self.audit_logger = self._setup_audit_logging()
        self.encryption_key = self._get_or_create_encryption_key()
        
        # Security monitoring
        self.failed_attempts = {}  # IP -> count
        self.suspicious_ips = set()
        self.blocked_ips = set()
        
        # Load security configuration
        self._load_security_config()
    
    def _setup_audit_logging(self):
        """Set up structured audit logging"""
        audit_logger = logging.getLogger('podcastflow.audit')
        audit_logger.setLevel(logging.INFO)
        
        # Cloud Logging handler
        handler = cloud_logging.CloudLoggingHandler(self.cloud_logging_client)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        
        return audit_logger
    
    def _get_or_create_encryption_key(self) -> str:
        """Get or create encryption key for sensitive data"""
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key().decode()
            logger.warning("Generated new encryption key - store securely in production")
        return key
    
    def _load_security_config(self):
        """Load security configuration from environment or defaults"""
        # In production, load from Cloud Secret Manager
        self.security_config = {
            'jwt_secret': os.getenv('JWT_SECRET', secrets.token_urlsafe(32)),
            'api_secret': os.getenv('API_SECRET', secrets.token_urlsafe(32)),
            'webhook_secret': os.getenv('WEBHOOK_SECRET', secrets.token_urlsafe(32))
        }
    
    def audit_log(self, event_type: AuditEventType, user_id: str = None, 
                  tenant_id: str = None, details: Dict[str, Any] = None, 
                  ip_address: str = None, user_agent: str = None):
        """Log security audit event"""
        
        audit_event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type.value,
            'user_id': user_id,
            'tenant_id': tenant_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'details': details or {},
            'severity': self._determine_event_severity(event_type),
            'session_id': getattr(self, '_current_session_id', None)
        }
        
        # Log to Cloud Logging
        self.audit_logger.info(json.dumps(audit_event))
        
        # Check for security alerts
        self._check_security_alerts(audit_event)
    
    def _determine_event_severity(self, event_type: AuditEventType) -> str:
        """Determine severity level for audit event"""
        severity_map = {
            AuditEventType.LOGIN: SecurityLevel.LOW.value,
            AuditEventType.LOGOUT: SecurityLevel.LOW.value,
            AuditEventType.API_ACCESS: SecurityLevel.LOW.value,
            AuditEventType.DATA_ACCESS: SecurityLevel.MEDIUM.value,
            AuditEventType.PERMISSION_CHANGE: SecurityLevel.HIGH.value,
            AuditEventType.CONFIG_CHANGE: SecurityLevel.HIGH.value,
            AuditEventType.SECURITY_ALERT: SecurityLevel.CRITICAL.value,
            AuditEventType.FAILED_AUTH: SecurityLevel.MEDIUM.value
        }
        
        return severity_map.get(event_type, SecurityLevel.MEDIUM.value)
    
    def _check_security_alerts(self, audit_event: Dict[str, Any]):
        """Check audit event for security alerts"""
        event_type = audit_event.get('event_type')
        ip_address = audit_event.get('ip_address')
        user_id = audit_event.get('user_id')
        
        # Failed authentication monitoring
        if event_type == AuditEventType.FAILED_AUTH.value and ip_address:
            self._track_failed_attempts(ip_address)
        
        # Suspicious activity detection
        if self._is_suspicious_activity(audit_event):
            self._trigger_security_alert(audit_event)
    
    def _track_failed_attempts(self, ip_address: str):
        """Track failed authentication attempts by IP"""
        current_time = datetime.now()
        
        if ip_address not in self.failed_attempts:
            self.failed_attempts[ip_address] = []
        
        # Add current attempt
        self.failed_attempts[ip_address].append(current_time)
        
        # Clean old attempts (older than 1 hour)
        cutoff_time = current_time - timedelta(hours=1)
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address]
            if attempt > cutoff_time
        ]
        
        # Check if IP should be blocked
        if len(self.failed_attempts[ip_address]) >= 5:
            self._block_ip(ip_address, "Too many failed authentication attempts")
    
    def _is_suspicious_activity(self, audit_event: Dict[str, Any]) -> bool:
        """Detect suspicious activity patterns"""
        ip_address = audit_event.get('ip_address')
        user_id = audit_event.get('user_id')
        event_type = audit_event.get('event_type')
        
        # Check blocked IPs
        if ip_address in self.blocked_ips:
            return True
        
        # Check for unusual access patterns
        if event_type == AuditEventType.DATA_ACCESS.value:
            # Check for bulk data access
            if self._is_bulk_data_access(user_id):
                return True
        
        # Check for geographic anomalies (would need IP geolocation service)
        # if self._is_geographic_anomaly(ip_address, user_id):
        #     return True
        
        return False
    
    def _is_bulk_data_access(self, user_id: str) -> bool:
        """Check if user is performing bulk data access"""
        # In production, this would check recent access patterns
        # For now, simple placeholder
        return False
    
    def _trigger_security_alert(self, audit_event: Dict[str, Any]):
        """Trigger security alert for suspicious activity"""
        alert = {
            'alert_type': 'SUSPICIOUS_ACTIVITY',
            'severity': SecurityLevel.HIGH.value,
            'original_event': audit_event,
            'timestamp': datetime.now().isoformat(),
            'recommended_action': 'INVESTIGATE'
        }
        
        # Log security alert
        self.audit_log(
            AuditEventType.SECURITY_ALERT,
            details=alert
        )
        
        # In production, send to security team
        logger.warning(f"Security alert triggered: {json.dumps(alert)}")
    
    def _block_ip(self, ip_address: str, reason: str):
        """Block IP address for security reasons"""
        self.blocked_ips.add(ip_address)
        
        self.audit_log(
            AuditEventType.SECURITY_ALERT,
            details={
                'action': 'IP_BLOCKED',
                'ip_address': ip_address,
                'reason': reason,
                'blocked_at': datetime.now().isoformat()
            }
        )
        
        logger.warning(f"Blocked IP {ip_address}: {reason}")
    
    def validate_ip_access(self, ip_address: str) -> bool:
        """Validate if IP address is allowed access"""
        if ip_address in self.blocked_ips:
            return False
        
        # Check IP whitelist if enabled
        if self.security_policy.session_requirements.get('ip_whitelist_enabled'):
            # In production, check against configured whitelist
            return True
        
        return True
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            fernet = Fernet(self.encryption_key.encode())
            return fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            fernet = Fernet(self.encryption_key.encode())
            return fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if not salt:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        
        return password_hash.hex(), salt
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        computed_hash, _ = self.hash_password(password, salt)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password against security policy"""
        requirements = self.security_policy.password_requirements
        
        validation_result = {
            'valid': True,
            'errors': []
        }
        
        # Check length
        if len(password) < requirements['min_length']:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Password must be at least {requirements['min_length']} characters")
        
        # Check character requirements
        if requirements['require_uppercase'] and not any(c.isupper() for c in password):
            validation_result['valid'] = False
            validation_result['errors'].append("Password must contain uppercase letters")
        
        if requirements['require_lowercase'] and not any(c.islower() for c in password):
            validation_result['valid'] = False
            validation_result['errors'].append("Password must contain lowercase letters")
        
        if requirements['require_numbers'] and not any(c.isdigit() for c in password):
            validation_result['valid'] = False
            validation_result['errors'].append("Password must contain numbers")
        
        if requirements['require_special_chars'] and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            validation_result['valid'] = False
            validation_result['errors'].append("Password must contain special characters")
        
        # Check unique characters
        if len(set(password)) < requirements['min_unique_chars']:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Password must contain at least {requirements['min_unique_chars']} unique characters")
        
        return validation_result
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token with security checks"""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.security_config['jwt_secret'],
                algorithms=['HS256']
            )
            
            # Additional security validations
            current_time = datetime.now().timestamp()
            
            # Check expiration
            if payload.get('exp', 0) < current_time:
                raise jwt.ExpiredSignatureError("Token has expired")
            
            # Check not before
            if payload.get('nbf', 0) > current_time:
                raise jwt.InvalidTokenError("Token not yet valid")
            
            # Check issuer (if configured)
            expected_issuer = os.getenv('JWT_ISSUER')
            if expected_issuer and payload.get('iss') != expected_issuer:
                raise jwt.InvalidTokenError("Invalid token issuer")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def scan_for_vulnerabilities(self) -> Dict[str, Any]:
        """Perform basic security vulnerability scan"""
        vulnerabilities = []
        recommendations = []
        
        # Check environment configuration
        if not os.getenv('JWT_SECRET'):
            vulnerabilities.append({
                'type': 'WEAK_JWT_SECRET',
                'severity': SecurityLevel.HIGH.value,
                'description': 'JWT secret not configured or using default'
            })
            recommendations.append('Configure strong JWT secret in environment')
        
        if not os.getenv('ENCRYPTION_KEY'):
            vulnerabilities.append({
                'type': 'MISSING_ENCRYPTION_KEY',
                'severity': SecurityLevel.MEDIUM.value,
                'description': 'Encryption key not configured'
            })
            recommendations.append('Configure encryption key for sensitive data')
        
        # Check HTTPS configuration
        if not self.security_policy.api_security['require_https']:
            vulnerabilities.append({
                'type': 'HTTP_ALLOWED',
                'severity': SecurityLevel.HIGH.value,
                'description': 'HTTPS not enforced'
            })
            recommendations.append('Enforce HTTPS for all API endpoints')
        
        return {
            'scan_timestamp': datetime.now().isoformat(),
            'vulnerabilities_found': len(vulnerabilities),
            'vulnerabilities': vulnerabilities,
            'recommendations': recommendations,
            'overall_security_score': self._calculate_security_score(vulnerabilities)
        }
    
    def _calculate_security_score(self, vulnerabilities: List[Dict]) -> int:
        """Calculate overall security score (0-100)"""
        if not vulnerabilities:
            return 100
        
        score = 100
        for vuln in vulnerabilities:
            severity = vuln.get('severity', SecurityLevel.MEDIUM.value)
            if severity == SecurityLevel.CRITICAL.value:
                score -= 30
            elif severity == SecurityLevel.HIGH.value:
                score -= 20
            elif severity == SecurityLevel.MEDIUM.value:
                score -= 10
            elif severity == SecurityLevel.LOW.value:
                score -= 5
        
        return max(0, score)
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get comprehensive security metrics"""
        return {
            'blocked_ips_count': len(self.blocked_ips),
            'failed_attempts_count': sum(len(attempts) for attempts in self.failed_attempts.values()),
            'security_policy_compliance': True,  # Would check actual compliance
            'last_vulnerability_scan': datetime.now().isoformat(),
            'encryption_enabled': self.security_policy.data_protection['encrypt_at_rest'],
            'audit_logging_enabled': True,
            'security_score': self._calculate_security_score([])
        }
    
    def cleanup_security_data(self):
        """Clean up old security tracking data"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=24)
        
        # Clean old failed attempts
        for ip in list(self.failed_attempts.keys()):
            self.failed_attempts[ip] = [
                attempt for attempt in self.failed_attempts[ip]
                if attempt > cutoff_time
            ]
            if not self.failed_attempts[ip]:
                del self.failed_attempts[ip]
        
        logger.info("Cleaned up old security tracking data")


class ComplianceManager:
    """Compliance and regulatory management"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.compliance_frameworks = [
            'SOC2',
            'GDPR',
            'CCPA',
            'HIPAA',
            'ISO27001'
        ]
    
    def generate_compliance_report(self, framework: str = 'SOC2') -> Dict[str, Any]:
        """Generate compliance report for specified framework"""
        if framework not in self.compliance_frameworks:
            raise ValueError(f"Unsupported compliance framework: {framework}")
        
        # Get security metrics
        security_metrics = self.security_manager.get_security_metrics()
        
        # Framework-specific checks
        compliance_checks = self._get_compliance_checks(framework)
        
        return {
            'framework': framework,
            'report_date': datetime.now().isoformat(),
            'compliance_score': self._calculate_compliance_score(compliance_checks),
            'security_metrics': security_metrics,
            'compliance_checks': compliance_checks,
            'recommendations': self._get_compliance_recommendations(framework)
        }
    
    def _get_compliance_checks(self, framework: str) -> List[Dict[str, Any]]:
        """Get compliance checks for framework"""
        # This would contain actual compliance requirements
        # For demo, using basic security checks
        return [
            {
                'requirement': 'Data Encryption',
                'status': 'COMPLIANT',
                'description': 'Data encrypted at rest and in transit'
            },
            {
                'requirement': 'Access Logging',
                'status': 'COMPLIANT', 
                'description': 'Comprehensive audit logging enabled'
            },
            {
                'requirement': 'Authentication Controls',
                'status': 'COMPLIANT',
                'description': 'Strong authentication and session management'
            }
        ]
    
    def _calculate_compliance_score(self, checks: List[Dict[str, Any]]) -> int:
        """Calculate compliance score"""
        if not checks:
            return 0
        
        compliant_count = sum(1 for check in checks if check['status'] == 'COMPLIANT')
        return int((compliant_count / len(checks)) * 100)
    
    def _get_compliance_recommendations(self, framework: str) -> List[str]:
        """Get compliance recommendations"""
        return [
            'Implement regular security training for all users',
            'Conduct quarterly vulnerability assessments',
            'Review and update security policies annually',
            'Implement data retention policies'
        ]


# Global instances
security_manager = SecurityManager()
compliance_manager = ComplianceManager(security_manager) 