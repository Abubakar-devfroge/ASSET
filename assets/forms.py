from django import forms
from django.contrib.auth.models import User
from .models import Asset, AssetRequest

class AssetForm(forms.ModelForm):
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Not Assigned",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Asset
        fields = [
            'serial_no',
            'purchase_date',
            'purchase_cost',
            'condition',
            'depreciation',
            'supplier',
            'warranty',
            'description',
            'category',
            'department',
            'status',
            'assigned_to',
            'image'
        ]
        widgets = {
            'serial_no': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'purchase_cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'condition': forms.TextInput(attrs={'class': 'form-control'}),
            'depreciation': forms.NumberInput(attrs={'class': 'form-control'}),
            'supplier': forms.TextInput(attrs={'class': 'form-control'}),
            'warranty': forms.TextInput(attrs={'class': 'form-control'}),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter a description of the asset...'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }

class AssetRequestForm(forms.ModelForm):
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Please explain why you need this asset...'
        }),
        required=True
    )

    class Meta:
        model = AssetRequest
        fields = ['purpose']
