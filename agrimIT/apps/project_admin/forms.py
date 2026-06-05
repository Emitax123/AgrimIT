from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.template.defaultfilters import filesizeformat
from .models import Project, ProjectNote


# Allowed file types for project uploads sent to Supabase storage.
ALLOWED_UPLOAD_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'dwg', 'docx']
# Hard size limit per file. Mirrors FILE_UPLOAD_MAX_MEMORY_SIZE (10MB in prod).
MAX_UPLOAD_SIZE = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024)



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
    file_field = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS)],
    )

    def clean_file_field(self):
        file = self.cleaned_data['file_field']
        if file and file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f"El archivo supera el tamaño máximo permitido ({filesizeformat(MAX_UPLOAD_SIZE)})."
            )
        return file


class ProjectNoteForm(forms.ModelForm):
    """Formulario para crear y editar notas de proyecto"""
    class Meta:
        model = ProjectNote
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Ej: Visita a campo, Entrega de documentación...',
                'maxlength': '200'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Describe los detalles del evento o nota...',
                'rows': 4
            })
        }
        labels = {
            'title': 'Título',
            'description': 'Descripción'
        }

