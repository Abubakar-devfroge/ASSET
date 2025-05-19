from django.db import migrations

def create_initial_departments(apps, schema_editor):
    Department = apps.get_model('assets', 'Department')
    departments = [
        'General Department',
        'IT Department',
        'HR Department',
        'Finance Department'
    ]
    for dept_name in departments:
        Department.objects.create(name=dept_name)

class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_departments),
    ] 