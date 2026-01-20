# Alertas BORA por Email 🔔

Este sistema revisa automáticamente el Boletín Oficial de la República Argentina y te envía un correo electrónico cuando se publican nuevas **Leyes** o **Decretos**.

## Cómo funciona
1. El script revisa la web del BORA diariamente.
2. Filtra solo las normas de interés (Leyes/Decretos).
3. Si hay novedades, envía un correo con enlaces directos.
4. Usa GitHub Actions para ejecutarse "serverless" sin costo.

## Configuración Necesaria (Secrets)
Para que funcione, debes ir a **Settings > Secrets and variables > Actions** en tu repositorio y agregar:
- `SMTP_USER`: Tu correo (ej. tu_usuario@gmail.com).
- `SMTP_PASSWORD`: Tu "Contraseña de Aplicación" de Google (no tu clave normal).
- `EMAIL_RECEIVER`: Dirección donde quieres recibir los avisos.

## Permisos de Guardado
Recuerda configurar en **Settings > Actions > General > Workflow permissions** la opción **"Read and write permissions"** para que el bot pueda recordar qué leyes ya te envió.
