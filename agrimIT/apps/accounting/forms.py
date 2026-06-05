from .models import AccountMovement
from django import forms

class ManualAccountEntryForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )

    class Meta:
        model = AccountMovement
        fields = '__all__'
        exclude = ['account', 'user', 'created_at', 'created_by']
        widgets = {
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

   
