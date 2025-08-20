from django.db import models
from apps.users.models import User
from apps.clients.models import Client


class Project (models.Model):
    TYPE_CHOICES = (
        ('Estado Parcelario', 'Estado Parcelario'),
        ('Mensura', 'Mensura'),
        ('Amojonamiento', 'Amojonamiento'),
        ('Relevamiento', 'Relevamiento'),
        ('Legajo Parcelario', 'Legajo Parcelario'),
        #Agregar una opcion de carga manual
        )
    MENS_CHOICES = (
        ('PH', 'PH'),
        ('Usucapion', 'Usucapion'),
        ('Division', 'Division'),
        ('Anexion/Division', 'Anexion/Division'),
        ('Unificacion', 'Unificacion'),
        )
    
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name='Proyecto')
    type_mens = models.CharField(null=True, blank=True, max_length=30, choices=MENS_CHOICES, verbose_name='Mensura')
    #Cliente
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, verbose_name='Cliente')

    #Titular, que puede o no puede ser el cliente
    titular_name = models.CharField(default="", max_length=100, verbose_name='Nombre y apellido')
    titular_phone = models.CharField(max_length=40, verbose_name='Telefono')
    
    #Nomenclatura
    partido= models.CharField(max_length=30, blank=True, verbose_name='Partido')
    partida= models.CharField(max_length=30, blank=True, verbose_name='Partida')
    circ= models.CharField(max_length=30, blank=True, verbose_name='Circunscripcion')
    sect= models.CharField(max_length=30, blank=True, verbose_name='Seccion')
    #Partida
    #Si hay chacra no hay quinta y vice
    chacra_num = models.CharField(max_length=10, blank=True, verbose_name='Numero')
    chacra_let= models.CharField(max_length=10, blank=True, verbose_name='Letra')

    quinta_num= models.CharField(max_length=10, blank=True, verbose_name='Numero')
    quinta_let= models.CharField(max_length=10, blank=True, verbose_name='Letra')
    
    fraccion_num = models.CharField(max_length=10, blank=True, verbose_name='Numero')
    fraccion_let = models.CharField(max_length=10, blank=True, verbose_name='Letra')
    
    manzana_num= models.CharField(max_length=10, blank=True, verbose_name='Numero')
    manzana_let= models.CharField(max_length=10, blank=True, verbose_name='Letra')

    parcela_num = models.CharField(max_length=10, blank=True, verbose_name='Numero')
    parcela_let = models.CharField(max_length=10, blank=True, verbose_name='Letra')
    
    subparcela = models.CharField(max_length=10, blank=True, verbose_name='Subparcela')


    street= models.CharField(max_length=50, blank=True, verbose_name='Calle')
    street_num = models.CharField(max_length=10, blank=True, verbose_name='Numero')
    floor = models.CharField(max_length=10, blank=True, verbose_name='Piso')
    dept = models.CharField(max_length=10, blank=True, verbose_name='Depto')

    INSC_CHOICES = (
        ('Folio','Folio'),
        ('Matricula','Matricula'),
        )
    inscription_type = models.CharField(null=True, max_length=30, default='', choices=INSC_CHOICES, verbose_name='Inscripcion')
    
    #Numero de tramite
    process_num = models.IntegerField(null=True, verbose_name='N° Tramite', blank=True)

    # Contact information
    contact_name = models.CharField(max_length=100, blank=True, verbose_name='Nombre de contacto')
    contact_phone = models.CharField(max_length=40, blank=True, verbose_name='Teléfono de contacto')
    
   
    procedure = models.CharField(max_length=100, blank=True, verbose_name='Procedimiento')
    
    # Status
    closed = models.BooleanField(default=False, verbose_name='Cerrado')
    
    #Accounting - Use string reference to avoid circular imports
    account = models.OneToOneField('accounting.Account', on_delete=models.CASCADE, null=True, blank=True, related_name='project')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuario')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.type} - {self.titular_name}"
    
    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user', 'created']),
            models.Index(fields=['partida']),
            models.Index(fields=['client', 'type']),
            models.Index(fields=['user', 'closed']),
        ]
    
class ProjectFiles (models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    name = models.CharField(max_length=255)  # File name in storage
    url = models.URLField()  # File URL from Supabase
    created = models.DateTimeField(auto_now_add=True)
    
    def get_filename(self):
        return self.name.split('/')[-1]
    
    class Meta:
        ordering = ['-created']
    
class Event (models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    TYPE_CHOICES = (
        ('modp', 'Modificacion'),
        ('newp', 'Nuevo'),
        ('deletep', 'Eliminacion'),
        ('file_add', 'Archivo Agregado'),
        ('file_del', 'Archivo Eliminado'),
        ('newc', 'Cliente Modificado'),
        ('deletec', 'Cliente Eliminado'),
    )
    time = models.DateTimeField(auto_now_add=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, related_name='events')
    project_pk = models.IntegerField(null=True, blank=True)  # Store project ID for quick access
    client_pk = models.IntegerField(null=True, blank=True)  # Store client ID for quick access
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    msg = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.type} - {self.project} - {self.time}"
    
    class Meta:
        ordering = ['-time']
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        indexes = [
            models.Index(fields=['project', '-time']),  # For efficient project history queries
            models.Index(fields=['type']),
            models.Index(fields=['user', '-time']),  # For history queries
            models.Index(fields=['project', 'type']), # For project history
        ]