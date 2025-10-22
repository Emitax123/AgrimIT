# 🚀 CONFIGURACIÓN DE LOGGING PARA RAILWAY

# Guía paso a paso para monitorear tu aplicación

## 📋 PASO 1: Verificar la configuración

# 1. Los logs de Django ahora están configurados en formato JSON

# 2. Frontend errors se envían al backend automáticamente

# 3. Se eliminaron todos los console.log statements

## 🔍 PASO 2: Ver logs en Railway

### Logs en tiempo real:

railway logs --follow

### Filtrar por nivel de error:

railway logs --level error

### Logs de las últimas 2 horas:

railway logs --since 2h

### Buscar logs específicos:

railway logs | grep "File upload"
railway logs | grep "Project created"
railway logs | grep "Frontend JavaScript error"

## 📊 PASO 3: Tipos de logs que verás

### Logs de proyectos:

{
"level": "INFO",
"time": "2025-10-22T10:30:00Z",
"module": "apps.project_admin.views",
"message": "Project created successfully",
"user_id": 123,
"project_id": 456,
"project_type": "Mensura",
"client_name": "Juan Pérez"
}

### Logs de upload de archivos:

{
"level": "INFO",
"time": "2025-10-22T10:35:00Z",
"module": "apps.project_admin.views",
"message": "File upload successful",
"user_id": 123,
"project_id": 456,
"filename": "plano.pdf",
"file_size": 2048000
}

### Logs de errores frontend:

{
"level": "ERROR",
"time": "2025-10-22T10:40:00Z",
"module": "apps.project_admin.views",
"message": "Frontend JavaScript error",
"user_id": 123,
"error_message": "Cannot read property 'value' of null",
"filename": "form.html",
"line_number": 25,
"url": "https://agrimit.up.railway.app/create/"
}

## 🎯 PASO 4: Alertas y monitoreo

### Para errores críticos, puedes configurar alertas:

railway logs --level error --follow | while read line; do
echo "🚨 ERROR: $line" # Aquí puedes agregar notificaciones
done

## 💡 PASO 5: Usar el nuevo sistema de logging

### En JavaScript (reemplaza console.log):

Logger.info("User clicked create button", {
form_type: "project_creation",
user_action: "button_click"
});

Logger.formValidation("project_form", true, {});

Logger.fileUpload("documento.pdf", 1024000, true);

### En Python (ya implementado):

logger.info("Custom message", extra={
'user_id': request.user.id,
'custom_field': 'custom_value'
})

## 🔧 PASO 6: Variables de entorno en Railway

# Asegúrate de tener estas variables configuradas:

DJANGO_SETTINGS_MODULE=agrimIT.settings.prod
SECRET_KEY=tu-secret-key-segura
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...
SUPABASE_BUCKET=tu-bucket

## 📈 PASO 7: Monitoreo de rendimiento

# Los logs incluyen información de rendimiento:

# - Tiempo de respuesta de requests

# - Errores de base de datos

# - Fallos de upload de archivos

# - Validaciones de formularios

## ⚠️ NOTAS IMPORTANTES

1. Los logs se mantienen por 7 días en Railway (plan gratuito)
2. Para logs de larga duración, considera exportar a un servicio externo
3. Los errores críticos aparecen inmediatamente en Railway logs
4. El formato JSON facilita el análisis automatizado

## 🎛️ COMANDOS ÚTILES

# Ver errores recientes:

railway logs --level error --tail 50

# Monitorear uploads:

railway logs | grep "File upload"

# Ver actividad de usuarios:

railway logs | grep "user_id"

# Exportar logs:

railway logs --since 24h > logs\_$(date +%Y%m%d).txt
