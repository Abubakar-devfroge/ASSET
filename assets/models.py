from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.utils import IntegrityError

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

    asset_no = models.CharField(max_length=50, unique=True, editable=False, default='TEMP-ASSET-0000')
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

    def generate_asset_number(self):
        if not self.department or not self.category:
            raise ValueError("Department and Category are required to generate asset number")

        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Get the last asset number for this department and category
                last_asset = Asset.objects.filter(
                    department=self.department,
                    category=self.category
                ).order_by('-asset_no').first()

                if last_asset and last_asset.asset_no:
                    try:
                        # Extract the number from the last asset number
                        last_number = int(last_asset.asset_no.split('-')[-1])
                        new_number = last_number + 1
                    except (ValueError, IndexError):
                        new_number = 1
                else:
                    new_number = 1

                # Format: [department]-[category]-KOTDA-[number]
                asset_no = f"{self.department.name}-{self.category}-KOTDA-{new_number:04d}"
                
                # Try to save with this number
                try:
                    with transaction.atomic():
                        # Double check if number exists
                        if not Asset.objects.filter(asset_no=asset_no).exists():
                            return asset_no
                except IntegrityError:
                    pass
                
                # If we get here, either the number exists or we got an integrity error
                # Try the next number
                attempt += 1
                continue
                    
            except Exception:
                attempt += 1
                continue
                
        raise ValueError("Could not generate a unique asset number after multiple attempts")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset_no} ({self.category})"

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
