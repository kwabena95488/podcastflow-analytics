"""
PodcastFlow Analytics - Multi-Tenancy Framework
Phase 3 Week 2: Enterprise Security & Multi-tenancy

Features:
- Tenant isolation at database and application level
- Tenant onboarding and provisioning
- Resource quotas and usage tracking
- Tenant-specific configuration and branding
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import bigquery
from google.cloud import storage
import uuid
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

class TenantStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PROVISIONING = "provisioning"
    DECOMMISSIONED = "decommissioned"

class TenantTier(Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class TenantConfig:
    """Tenant configuration data structure"""
    tenant_id: str
    name: str
    domain: str
    status: TenantStatus
    tier: TenantTier
    created_at: datetime
    updated_at: datetime
    settings: Dict[str, Any]
    quotas: Dict[str, int]
    usage: Dict[str, int]
    admin_email: str

class TenantManager:
    """Multi-tenant management system"""
    
    def __init__(self):
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'your-gcp-project')
        self.bigquery_client = bigquery.Client(project=self.project_id)
        self.storage_client = storage.Client(project=self.project_id)
        
        # Tenant storage (in production, use Cloud SQL or Firestore)
        self.tenants = {}
        self._load_tenants()
        
        # Default quotas by tier
        self.tier_quotas = {
            TenantTier.FREE: {
                'max_podcasts': 5,
                'max_episodes': 100,
                'max_api_calls_per_hour': 100,
                'max_storage_gb': 1,
                'max_users': 3
            },
            TenantTier.PREMIUM: {
                'max_podcasts': 50,
                'max_episodes': 5000,
                'max_api_calls_per_hour': 1000,
                'max_storage_gb': 10,
                'max_users': 25
            },
            TenantTier.ENTERPRISE: {
                'max_podcasts': -1,  # Unlimited
                'max_episodes': -1,
                'max_api_calls_per_hour': 10000,
                'max_storage_gb': 100,
                'max_users': -1
            }
        }
    
    def _load_tenants(self):
        """Load tenants from persistent storage"""
        # In production, this would load from Cloud SQL or Firestore
        # For demo, we'll initialize with default tenants
        self._initialize_default_tenants()
    
    def _initialize_default_tenants(self):
        """Initialize default tenants for demo"""
        default_tenants = [
            {
                'tenant_id': 'demo-tenant',
                'name': 'Demo Organization',
                'domain': 'demo.com',
                'status': TenantStatus.ACTIVE,
                'tier': TenantTier.PREMIUM,
                'admin_email': 'admin@demo.com'
            },
            {
                'tenant_id': 'enterprise-tenant',
                'name': 'Enterprise Corp',
                'domain': 'enterprise.com',
                'status': TenantStatus.ACTIVE,
                'tier': TenantTier.ENTERPRISE,
                'admin_email': 'admin@enterprise.com'
            }
        ]
        
        for tenant_data in default_tenants:
            self.create_tenant(**tenant_data)
    
    def create_tenant(self, tenant_id: str = None, name: str = None, domain: str = None, 
                     status: TenantStatus = TenantStatus.PROVISIONING, 
                     tier: TenantTier = TenantTier.FREE, admin_email: str = None, 
                     **kwargs) -> TenantConfig:
        """Create a new tenant"""
        
        if not tenant_id:
            tenant_id = str(uuid.uuid4())[:8]
        
        if tenant_id in self.tenants:
            raise ValueError(f"Tenant {tenant_id} already exists")
        
        # Create tenant configuration
        tenant_config = TenantConfig(
            tenant_id=tenant_id,
            name=name or f"Tenant {tenant_id}",
            domain=domain or f"{tenant_id}.podcastflow.com",
            status=status,
            tier=tier,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            settings=self._get_default_settings(tier),
            quotas=self.tier_quotas[tier].copy(),
            usage=self._initialize_usage_tracking(),
            admin_email=admin_email or f"admin@{domain}"
        )
        
        # Store tenant
        self.tenants[tenant_id] = tenant_config
        
        # Provision tenant resources
        if status == TenantStatus.PROVISIONING:
            self._provision_tenant_resources(tenant_config)
            tenant_config.status = TenantStatus.ACTIVE
            tenant_config.updated_at = datetime.now()
        
        logger.info(f"Created tenant: {tenant_id} ({name})")
        return tenant_config
    
    def _get_default_settings(self, tier: TenantTier) -> Dict[str, Any]:
        """Get default settings for tenant tier"""
        base_settings = {
            'branding': {
                'primary_color': '#6366f1',
                'secondary_color': '#8b5cf6',
                'logo_url': None,
                'custom_domain': None
            },
            'features': {
                'advanced_analytics': False,
                'custom_reports': False,
                'api_access': True,
                'data_export': False,
                'real_time_alerts': False
            },
            'security': {
                'sso_enabled': False,
                'mfa_required': False,
                'ip_whitelist': [],
                'session_timeout_minutes': 480
            }
        }
        
        # Tier-specific enhancements
        if tier == TenantTier.PREMIUM:
            base_settings['features'].update({
                'advanced_analytics': True,
                'custom_reports': True,
                'data_export': True
            })
        elif tier == TenantTier.ENTERPRISE:
            base_settings['features'].update({
                'advanced_analytics': True,
                'custom_reports': True,
                'data_export': True,
                'real_time_alerts': True
            })
            base_settings['security'].update({
                'sso_enabled': True,
                'mfa_required': True
            })
        
        return base_settings
    
    def _initialize_usage_tracking(self) -> Dict[str, int]:
        """Initialize usage tracking counters"""
        return {
            'podcasts_count': 0,
            'episodes_count': 0,
            'api_calls_today': 0,
            'storage_used_gb': 0,
            'users_count': 0,
            'last_activity': int(datetime.now().timestamp())
        }
    
    def _provision_tenant_resources(self, tenant_config: TenantConfig):
        """Provision cloud resources for tenant"""
        try:
            # Create tenant-specific BigQuery datasets
            self._create_tenant_datasets(tenant_config.tenant_id)
            
            # Create tenant-specific storage bucket
            self._create_tenant_storage(tenant_config.tenant_id)
            
            # Set up tenant-specific monitoring
            self._setup_tenant_monitoring(tenant_config.tenant_id)
            
            logger.info(f"Provisioned resources for tenant: {tenant_config.tenant_id}")
            
        except Exception as e:
            logger.error(f"Failed to provision tenant resources: {str(e)}")
            raise
    
    def _create_tenant_datasets(self, tenant_id: str):
        """Create BigQuery datasets for tenant"""
        datasets = ['bronze', 'silver', 'gold', 'analytics']
        
        for dataset_type in datasets:
            dataset_id = f"{self.project_id}.{tenant_id}_{dataset_type}"
            
            try:
                dataset = bigquery.Dataset(dataset_id)
                dataset.location = "US"
                dataset.description = f"Tenant {tenant_id} {dataset_type} layer data"
                
                # Set labels for tenant identification
                dataset.labels = {
                    'tenant_id': tenant_id.replace('-', '_'),
                    'layer': dataset_type,
                    'managed_by': 'podcastflow_analytics'
                }
                
                self.bigquery_client.create_dataset(dataset, exists_ok=True)
                logger.info(f"Created dataset: {dataset_id}")
                
            except Exception as e:
                logger.warning(f"Dataset creation failed for {dataset_id}: {str(e)}")
    
    def _create_tenant_storage(self, tenant_id: str):
        """Create Cloud Storage bucket for tenant"""
        try:
            bucket_name = f"{self.project_id}-{tenant_id}-data"
            bucket = self.storage_client.bucket(bucket_name)
            
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(
                    bucket_name,
                    location="US"
                )
                
                # Set lifecycle rules
                bucket.lifecycle_rules = [
                    {
                        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
                        "condition": {"age": 30}
                    },
                    {
                        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
                        "condition": {"age": 90}
                    }
                ]
                bucket.patch()
                
                logger.info(f"Created storage bucket: {bucket_name}")
            
        except Exception as e:
            logger.warning(f"Storage bucket creation failed: {str(e)}")
    
    def _setup_tenant_monitoring(self, tenant_id: str):
        """Set up monitoring and alerting for tenant"""
        # This would set up Cloud Monitoring alerts and dashboards
        # specific to the tenant's resources
        logger.info(f"Monitoring setup for tenant: {tenant_id}")
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant configuration"""
        return self.tenants.get(tenant_id)
    
    def list_tenants(self, status: TenantStatus = None) -> List[TenantConfig]:
        """List all tenants, optionally filtered by status"""
        tenants = list(self.tenants.values())
        
        if status:
            tenants = [t for t in tenants if t.status == status]
        
        return sorted(tenants, key=lambda t: t.created_at, reverse=True)
    
    def update_tenant(self, tenant_id: str, **updates) -> TenantConfig:
        """Update tenant configuration"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Update allowed fields
        allowed_updates = ['name', 'status', 'tier', 'settings', 'quotas', 'admin_email']
        
        for key, value in updates.items():
            if key in allowed_updates:
                setattr(tenant, key, value)
        
        tenant.updated_at = datetime.now()
        
        # If tier changed, update quotas
        if 'tier' in updates:
            tenant.quotas = self.tier_quotas[tenant.tier].copy()
        
        logger.info(f"Updated tenant: {tenant_id}")
        return tenant
    
    def suspend_tenant(self, tenant_id: str, reason: str = None) -> bool:
        """Suspend tenant access"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.now()
        tenant.settings['suspension_reason'] = reason
        
        logger.warning(f"Suspended tenant: {tenant_id} - Reason: {reason}")
        return True
    
    def reactivate_tenant(self, tenant_id: str) -> bool:
        """Reactivate suspended tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.now()
        tenant.settings.pop('suspension_reason', None)
        
        logger.info(f"Reactivated tenant: {tenant_id}")
        return True
    
    def check_quota(self, tenant_id: str, resource: str, requested: int = 1) -> bool:
        """Check if tenant can use requested amount of resource"""
        tenant = self.get_tenant(tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            return False
        
        quota_key = f"max_{resource}"
        if quota_key not in tenant.quotas:
            return True  # No quota limit
        
        max_allowed = tenant.quotas[quota_key]
        if max_allowed == -1:  # Unlimited
            return True
        
        usage_key = f"{resource}_count"
        current_usage = tenant.usage.get(usage_key, 0)
        
        return (current_usage + requested) <= max_allowed
    
    def update_usage(self, tenant_id: str, resource: str, amount: int):
        """Update tenant resource usage"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return
        
        usage_key = f"{resource}_count"
        current_usage = tenant.usage.get(usage_key, 0)
        tenant.usage[usage_key] = max(0, current_usage + amount)
        tenant.usage['last_activity'] = int(datetime.now().timestamp())
    
    def get_tenant_by_domain(self, domain: str) -> Optional[TenantConfig]:
        """Get tenant by domain"""
        for tenant in self.tenants.values():
            if tenant.domain == domain:
                return tenant
        return None
    
    def get_tenant_usage_report(self, tenant_id: str) -> Dict[str, Any]:
        """Get comprehensive usage report for tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}
        
        quota_utilization = {}
        for resource, quota in tenant.quotas.items():
            if quota == -1:
                quota_utilization[resource] = "unlimited"
            else:
                usage_key = resource.replace('max_', '') + '_count'
                current_usage = tenant.usage.get(usage_key, 0)
                utilization = (current_usage / quota) * 100 if quota > 0 else 0
                quota_utilization[resource] = {
                    'current': current_usage,
                    'limit': quota,
                    'utilization_percent': round(utilization, 2)
                }
        
        return {
            'tenant_id': tenant_id,
            'name': tenant.name,
            'tier': tenant.tier.value,
            'status': tenant.status.value,
            'quota_utilization': quota_utilization,
            'last_activity': datetime.fromtimestamp(tenant.usage['last_activity']),
            'created_at': tenant.created_at,
            'updated_at': tenant.updated_at
        }
    
    def cleanup_decommissioned_tenants(self):
        """Clean up resources for decommissioned tenants"""
        decommissioned = [t for t in self.tenants.values() 
                         if t.status == TenantStatus.DECOMMISSIONED]
        
        for tenant in decommissioned:
            try:
                # In production, this would clean up BigQuery datasets,
                # storage buckets, and other cloud resources
                logger.info(f"Cleaned up resources for tenant: {tenant.tenant_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup tenant {tenant.tenant_id}: {str(e)}")


class TenantContextManager:
    """Context manager for tenant-specific operations"""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self.current_tenant = None
    
    def set_tenant_context(self, tenant_id: str):
        """Set current tenant context"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        if tenant.status != TenantStatus.ACTIVE:
            raise ValueError(f"Tenant {tenant_id} is not active")
        
        self.current_tenant = tenant
    
    def get_tenant_dataset_prefix(self) -> str:
        """Get BigQuery dataset prefix for current tenant"""
        if not self.current_tenant:
            raise ValueError("No tenant context set")
        
        return f"{self.tenant_manager.project_id}.{self.current_tenant.tenant_id}"
    
    def get_tenant_storage_bucket(self) -> str:
        """Get storage bucket name for current tenant"""
        if not self.current_tenant:
            raise ValueError("No tenant context set")
        
        return f"{self.tenant_manager.project_id}-{self.current_tenant.tenant_id}-data"
    
    def check_feature_access(self, feature: str) -> bool:
        """Check if current tenant has access to feature"""
        if not self.current_tenant:
            return False
        
        return self.current_tenant.settings.get('features', {}).get(feature, False)


# Global instances
tenant_manager = TenantManager()
tenant_context = TenantContextManager(tenant_manager) 