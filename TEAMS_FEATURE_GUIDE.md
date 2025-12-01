# Guía de Funcionalidad: Grupos (Teams)

## Descripción General

La funcionalidad de Grupos permite a los usuarios de AgrimIT colaborar compartiendo proyectos entre sí. Los usuarios pueden crear grupos, agregar miembros, y compartir proyectos específicos con esos grupos.

## Características Principales

### 1. Gestión de Grupos

#### Crear un Grupo

- **Ubicación**: Menú "Grupos" → "Crear Grupo"
- **Funcionalidad**:
  - Nombre y descripción del grupo
  - Agregar miembros escribiendo sus nombres de usuario separados por comas
  - Ejemplo: `usuario1, usuario2, usuario3`
  - El creador del grupo automáticamente se convierte en el **propietario**

#### Ver Mis Grupos

- **Ubicación**: Menú "Grupos" → "Mis Grupos"
- **Muestra**:
  - Grupos donde eres propietario
  - Grupos donde eres miembro
  - Estadísticas: número de miembros y proyectos compartidos

#### Editar un Grupo

- Solo el **propietario** puede:
  - Modificar nombre y descripción
  - Agregar nuevos miembros
  - El propietario **no puede** agregarse como miembro

#### Eliminar un Grupo

- Solo el **propietario** puede eliminar el grupo
- Al eliminar un grupo, se eliminan todos los compartidos de proyectos asociados

### 2. Gestión de Miembros

#### Roles Disponibles

- **Propietario**: Creador del grupo (solo puede haber uno)
  - Control total del grupo
  - Puede agregar/eliminar miembros
  - Puede editar/eliminar el grupo
- **Miembro**: Usuario agregado al grupo

  - Puede ver proyectos compartidos
  - Puede ver información del grupo
  - No puede modificar el grupo

- **Visualizador**: (Funcionalidad futura)
  - Solo lectura de proyectos compartidos

#### Agregar Miembros

- Desde la vista de detalle del grupo
- Ingresar nombre de usuario del nuevo miembro
- Validaciones:
  - El usuario debe existir en el sistema
  - No se puede agregar al propietario como miembro
  - No se pueden agregar usuarios duplicados

#### Eliminar Miembros

- Solo el propietario puede eliminar miembros
- Se elimina desde la vista de detalle del grupo
- Confirmación requerida

### 3. Compartir Proyectos

#### Compartir un Proyecto

- **Desde el proyecto**:

  1. Abrir el proyecto que deseas compartir
  2. Click en el botón "👥 Compartir" (ubicado junto al botón "Eliminar")
  3. Seleccionar el grupo con el que deseas compartir
  4. (Opcional) Agregar notas sobre el compartido
  5. Click en "Compartir"

- **Validaciones**:
  - Solo el propietario del proyecto puede compartirlo
  - No se puede compartir un proyecto con el mismo grupo dos veces

#### Ver Proyectos Compartidos

- **Ubicación**: Menú "Grupos" → "Proyectos Compartidos"
- **Muestra todos los proyectos que otros usuarios han compartido contigo a través de tus grupos**
- **Información visible**:
  - Tipo de proyecto
  - Cliente
  - Titular
  - Partida
  - Fecha de creación
  - Grupo a través del cual fue compartido
  - Usuario que lo compartió
  - Notas (si las hay)

#### Dejar de Compartir

- **Ubicación**: Desde la vista del proyecto
- Solo el **propietario del proyecto** puede:
  - Ver con qué grupos está compartido el proyecto
  - Dejar de compartir con grupos específicos
- **Proceso**:
  1. Abrir el proyecto
  2. Ver la sección "Compartido con:"
  3. Click en "Dejar de compartir" junto al grupo
  4. Confirmación requerida

### 4. Seguridad y Permisos

#### Visibilidad

- Los usuarios **solo pueden ver**:
  - Grupos que ellos crearon
  - Grupos donde son miembros
  - Proyectos compartidos con sus grupos

#### Restricciones

- Un usuario **no puede**:
  - Ver grupos de otros usuarios
  - Modificar grupos donde no es propietario
  - Compartir proyectos que no le pertenecen
  - Acceder directamente a proyectos de otros usuarios (solo a través de compartidos)

## Modelos de Base de Datos

### Team (Grupo)

```python
- name: Nombre del grupo
- description: Descripción del grupo
- owner: Usuario propietario (ForeignKey)
- is_active: Estado del grupo
- created_at: Fecha de creación
```

### TeamMembership (Membresía)

```python
- team: Grupo (ForeignKey)
- user: Usuario miembro (ForeignKey)
- role: Rol (member/viewer)
- joined_at: Fecha de ingreso
- unique_together: (team, user) - Evita duplicados
```

### ProjectShare (Compartido)

```python
- project: Proyecto compartido (ForeignKey)
- team: Grupo con el que se comparte (ForeignKey)
- shared_by: Usuario que compartió (ForeignKey)
- shared_at: Fecha de compartido
- notes: Notas opcionales
- unique_together: (project, team) - Evita compartir dos veces
```

## URLs Disponibles

```python
/grupos/                          # Lista de grupos
/grupos/crear/                    # Crear grupo
/grupos/<id>/                     # Detalle del grupo
/grupos/<id>/editar/             # Editar grupo
/grupos/<id>/eliminar/           # Eliminar grupo
/grupos/<id>/agregar-miembro/    # Agregar miembro
/grupos/<team_id>/eliminar-miembro/<user_id>/  # Eliminar miembro
/grupos/proyectos-compartidos/   # Ver proyectos compartidos
/grupos/proyecto/<id>/compartir/  # Compartir proyecto
/grupos/proyecto/<project_id>/dejar-compartir/<team_id>/  # Dejar de compartir
```

## Casos de Uso Comunes

### Caso 1: Colaboración en Oficina

**Escenario**: Una oficina de agrimensura con 5 profesionales

1. El jefe crea un grupo "Equipo Principal"
2. Agrega a los 4 agrimensores como miembros
3. Cada agrimensor comparte sus proyectos en curso con el grupo
4. Todo el equipo puede ver el estado de todos los proyectos

### Caso 2: Proyecto Conjunto

**Escenario**: Dos agrimensores trabajan juntos en un proyecto grande

1. Agrimensor A crea un grupo "Proyecto Loteo San Juan"
2. Agrega al Agrimensor B como miembro
3. Ambos comparten sus proyectos relacionados con ese loteo
4. Pueden ver mutuamente el progreso

### Caso 3: Supervisión

**Escenario**: Un agrimensor senior supervisa a varios juniors

1. Senior crea grupo "Supervisados 2024"
2. Agrega a los agrimensores junior como miembros
3. Los juniors comparten sus proyectos con el grupo
4. El senior puede revisar todos los trabajos desde "Proyectos Compartidos"

## Estilos y Diseño

- **Diseño Responsivo**: Funciona en móviles, tablets y desktop
- **Tarjetas (Cards)**: Cada grupo/proyecto se muestra como una tarjeta
- **Badges**: Identificadores visuales para propietario/miembro
- **Colores**:
  - Verde (#2c5f2d): Temas principales, botones de acción
  - Rojo (#c9302c): Botones de eliminar/peligro
  - Gris (#f5f5f5): Fondos de tarjetas
  - Azul (#007bff): Enlaces y acciones secundarias

## Navegación

El menú "Grupos" está ubicado en la barra de navegación principal y contiene:

1. **Mis Grupos**: Ver todos tus grupos (propios y donde eres miembro)
2. **Crear Grupo**: Formulario para crear un nuevo grupo
3. **Proyectos Compartidos**: Ver todos los proyectos compartidos contigo

## Notificaciones y Mensajes

El sistema muestra mensajes usando Django Messages Framework:

- ✅ **Éxito**: "Grupo creado correctamente", "Proyecto compartido", etc.
- ⚠️ **Advertencia**: "Ya eres miembro de este grupo", etc.
- ❌ **Error**: "No tienes permiso", "Usuario no encontrado", etc.

## Mejoras Futuras Sugeridas

1. **Notificaciones por Email**: Avisar cuando te agregan a un grupo o comparten un proyecto
2. **Permisos Granulares**: Permitir diferentes niveles de acceso (lectura, edición, comentarios)
3. **Historial de Cambios**: Ver quién agregó/removió miembros o compartió proyectos
4. **Búsqueda**: Buscar dentro de proyectos compartidos
5. **Exportación**: Exportar lista de proyectos compartidos a PDF/Excel
6. **Chat/Comentarios**: Permitir comentarios en proyectos compartidos
7. **Estadísticas**: Dashboard con métricas de colaboración

## Soporte y Troubleshooting

### Problema: "No puedo agregar un miembro"

- **Solución**: Verifica que el nombre de usuario sea exacto (case-sensitive)
- Asegúrate de que el usuario esté registrado en el sistema
- Verifica que no sea el propietario del grupo

### Problema: "No veo el botón de compartir en mi proyecto"

- **Solución**: El botón solo aparece si eres el propietario del proyecto
- Verifica que hayas iniciado sesión con la cuenta correcta

### Problema: "No puedo eliminar un grupo"

- **Solución**: Solo el propietario puede eliminar grupos
- Si eres miembro, pide al propietario que te elimine del grupo

---

**Versión**: 1.0  
**Fecha**: 2024  
**Desarrollador**: AgrimIT Team
