from django import forms
from .models import Project



class DecimalForm(forms.ModelForm):
     dec = forms.DecimalField(max_digits=8, decimal_places=2)

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        exclude = ['user', 'client', 'inscription_type', 'procedure', 'files', 'contact_name', 'contact_phone']
    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.fields['titular_name'].required = False
        self.fields['titular_phone'].required = False
        if 'type_mens' in self.fields:
            self.fields['type_mens'].required = False

class ProjectFullForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        exclude = [
            'user', 'type', 'client','contact_name','contact_phone','titular_name', 
            'titular_phone','inscription_type', 
            'procedure', 'files', 'closed'
        ]
    
    def __init__(self, *args, **kwargs):
        super(ProjectFullForm, self).__init__(*args, **kwargs)
        self.fields['titular_name'].required = False
        self.fields['titular_phone'].required = False
        self.fields['mens'].required = False

    def __init__(self, *args, **kwargs):
        super(ProjectFullForm, self).__init__(*args, **kwargs)
        self.fields['chacra_num'].label = "Chacra Num"
        self.fields['chacra_let'].label = "Chacra Letra"
        self.fields['quinta_num'].label = "Quinta Num"
        self.fields['quinta_let'].label = "Quinta Letra"
        self.fields['parcela_num'].label = "Parcela Num"
        self.fields['parcela_let'].label = "Parcela Letra"
        self.fields['manzana_num'].label = "Manzana Num"
        self.fields['manzana_let'].label = "Manzana Letra"
        self.fields['fraccion_num'].label = "Fraccion Num"
        self.fields['fraccion_let'].label = "Fraccion Letra"





        

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class FileFieldForm(forms.Form):
    file_field = forms.FileField()

