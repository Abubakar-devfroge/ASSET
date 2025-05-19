from django.core.management.base import BaseCommand
from assets.models import Asset

class Command(BaseCommand):
    help = 'Updates asset numbers for existing assets'

    def handle(self, *args, **kwargs):
        assets = Asset.objects.filter(asset_no__isnull=True)
        count = 0
        
        for asset in assets:
            if asset.department and asset.category:
                asset.asset_no = asset.generate_asset_number()
                asset.save()
                count += 1
                self.stdout.write(f'Updated asset number for asset {asset.id}: {asset.asset_no}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} asset numbers')) 