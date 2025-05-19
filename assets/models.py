from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Asset(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired')
    ]

    CATEGORY_CHOICES = [
        ('furniture', 'Furniture'),
        ('technology', 'Technology'),
        ('vehicles', 'Vehicles'),
        ('office_supplies', 'Office Supplies'),
        ('machinery', 'Machinery / Equipment')
    ]

    serial_no = models.CharField(max_length=100, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    condition = models.CharField(max_length=100, null=True, blank=True)
    depreciation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Depreciation rate in %")
    supplier = models.CharField(max_length=255, null=True, blank=True)
    warranty = models.CharField(max_length=100, null=True, blank=True)

    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='assets/', null=True, blank=True)

    def __str__(self):
        return f"{self.serial_no} ({self.category})"

    class Meta:
        ordering = ['-created_at']

class AssetRequest(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='asset_requests')
    purpose = models.TextField(help_text="Please explain why you need this asset", null=True, blank=True)
    request_date = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Request for {self.asset.serial_no} by {self.user.username}"

    class Meta:
        ordering = ['-request_date']
