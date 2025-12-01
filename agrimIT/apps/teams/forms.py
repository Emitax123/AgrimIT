from django import forms
from django.contrib.auth import get_user_model
from .models import Team, TeamMembership, ProjectShare

User = get_user_model()


class TeamForm(forms.ModelForm):
    """
    Formulario para crear y editar equipos de trabajo
    """
    members_usernames = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Ingrese los nombres de usuario separados por comas (ej: usuario1, usuario2, usuario3)',
            'class': 'form-control'
        }),
        label='Miembros del Equipo',
        help_text='Escriba los nombres de usuario de las personas que desea agregar, separados por comas.'
    )
    
    class Meta:
        model = Team
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del grupo'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descripción del grupo (opcional)'
            }),
        }
        labels = {
            'name': 'Nombre del Grupo',
            'description': 'Descripción',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Si estamos editando, prellenar con los miembros actuales
        if self.instance.pk:
            members = TeamMembership.objects.filter(
                team=self.instance, 
                is_active=True
            ).select_related('user')
            usernames = ', '.join([m.user.username for m in members])
            self.fields['members_usernames'].initial = usernames
    
    def clean_members_usernames(self):
        """Validar que los usuarios existan"""
        usernames_str = self.cleaned_data.get('members_usernames', '')
        
        if not usernames_str.strip():
            return []
        
        # Separar por comas y limpiar espacios
        usernames = [u.strip() for u in usernames_str.split(',') if u.strip()]
        
        # Validar que los usuarios existan
        valid_users = []
        invalid_usernames = []
        
        for username in usernames:
            try:
                user = User.objects.get(username=username)
                # No permitir que el propietario se agregue como miembro
                if self.user and user == self.user:
                    continue
                valid_users.append(user)
            except User.DoesNotExist:
                invalid_usernames.append(username)
        
        if invalid_usernames:
            raise forms.ValidationError(
                f"Los siguientes usuarios no existen: {', '.join(invalid_usernames)}"
            )
        
        return valid_users
    
    def clean_name(self):
        """Validar que el nombre no esté duplicado para este usuario"""
        name = self.cleaned_data.get('name')
        
        if self.user:
            # Si estamos editando, excluir el equipo actual de la búsqueda
            teams = Team.objects.filter(owner=self.user, name=name, is_active=True)
            if self.instance.pk:
                teams = teams.exclude(pk=self.instance.pk)
            
            if teams.exists():
                raise forms.ValidationError(
                    f'Ya tienes un grupo llamado "{name}". Por favor elige otro nombre.'
                )
        
        return name


class AddMemberForm(forms.Form):
    """
    Formulario simple para agregar un miembro a un equipo existente
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario'
        }),
        label='Usuario a Agregar'
    )
    
    role = forms.ChoiceField(
        choices=TeamMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Rol',
        initial='viewer'
    )
    
    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
    
    def clean_username(self):
        """Validar que el usuario exista y no esté ya en el equipo"""
        username = self.cleaned_data.get('username')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError(f'El usuario "{username}" no existe.')
        
        # Verificar que no sea el propietario
        if self.team and user == self.team.owner:
            raise forms.ValidationError('No puedes agregar al propietario del grupo como miembro.')
        
        # Verificar que no esté ya en el equipo
        if self.team:
            existing = TeamMembership.objects.filter(
                team=self.team,
                user=user,
                is_active=True
            ).exists()
            
            if existing:
                raise forms.ValidationError(f'El usuario "{username}" ya es miembro de este grupo.')
        
        return user


class ShareProjectForm(forms.ModelForm):
    """
    Formulario para compartir un proyecto con un equipo
    """
    class Meta:
        model = ProjectShare
        fields = ['team', 'notes']
        widgets = {
            'team': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales (opcional)'
            }),
        }
        labels = {
            'team': 'Compartir con Grupo',
            'notes': 'Notas',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar solo los equipos del usuario actual
        if self.user:
            self.fields['team'].queryset = Team.objects.filter(
                owner=self.user,
                is_active=True
            ).order_by('name')
        
        # Si no hay equipos disponibles
        if not self.fields['team'].queryset.exists():
            self.fields['team'].widget.attrs['disabled'] = True
            self.fields['team'].help_text = 'No tienes grupos creados. Crea un grupo primero.'
    
    def clean_team(self):
        """Validar que el proyecto no esté ya compartido con este equipo"""
        team = self.cleaned_data.get('team')
        
        if self.project and team:
            existing = ProjectShare.objects.filter(
                project=self.project,
                team=team,
                is_active=True
            ).exists()
            
            if existing:
                raise forms.ValidationError(
                    f'Este proyecto ya está compartido con el grupo "{team.name}".'
                )
        
        return team
