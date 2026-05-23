# SmartSchedule — Generador Inteligente de Horarios de Estudio

## 🌐 Aplicación en producción
https://ing-de-software-cyqy.onrender.com

**Universidad:** USFX — Ingeniería de Software  
**Grupo:** 3

## Integrantes

| Nombre | Rol |
|--------|-----|
| Erick Manuel Arancibia Flores | Desarrollador |
| Jhonn Wilder Llanos Rojas | Desarrollador |
| Camila Fernanda Montecinos Solis | Desarrolladora |

## Descripción

SmartSchedule es una aplicación web que permite a estudiantes universitarios organizar su tiempo de estudio y a oferentes publicar tutorías, cursos y materiales educativos. Los administradores gestionan usuarios y validan el contenido publicado.

### Funcionalidades principales

- **Autenticación** por roles: admin, ofertante, demandante
- **Gestión de usuarios** (CRUD completo — solo admin)
- **Publicación de productos/servicios** (ofertantes)
- **Validación de contenido** (admin aprueba/rechaza)
- **Visualización de productos** aprobados (demandantes)

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Node.js + Express |
| Base de datos | SQLite (better-sqlite3) |
| Frontend | HTML + CSS + JavaScript vanilla |
| Sesiones | express-session |
| Despliegue | Render.com |

## Ejecutar localmente

```bash
# 1. Instalar dependencias
npm install

# 2. Iniciar el servidor
npm start

# 3. Abrir en el navegador
# http://localhost:3000
```

### Usuarios de prueba

| Username | Contraseña | Rol |
|----------|-----------|-----|
| admin | admin123 | Administrador |
| ofertante1 | pass123 | Ofertante |
| demandante1 | pass123 | Demandante |

## Endpoints API

### Autenticación `/api/auth`

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /api/auth/login | Iniciar sesión |
| POST | /api/auth/logout | Cerrar sesión |
| GET | /api/auth/me | Usuario actual |

### Usuarios `/api/users`

| Método | Ruta | Descripción | Rol requerido |
|--------|------|-------------|---------------|
| GET | /api/users | Listar todos | admin |
| GET | /api/users/:id | Ver uno | auth |
| POST | /api/users | Crear | admin |
| PUT | /api/users/:id | Editar | auth (propio o admin) |
| DELETE | /api/users/:id | Eliminar | admin |

### Productos `/api/products`

| Método | Ruta | Descripción | Rol requerido |
|--------|------|-------------|---------------|
| GET | /api/products | Listar (filtrado por rol) | auth |
| GET | /api/products/pending | Solo pendientes | admin |
| GET | /api/products/:id | Ver uno | auth |
| POST | /api/products | Crear | ofertante/admin |
| PUT | /api/products/:id | Editar | ofertante (propio)/admin |
| DELETE | /api/products/:id | Eliminar | ofertante (propio)/admin |
| PATCH | /api/products/:id/status | Cambiar estado | admin |

## Despliegue en Render

**URL:** https://smartschedule-g3.onrender.com

**Configuración en Render:**
- **Build command:** `npm install`
- **Start command:** `npm start`
- **Environment:** Node

> La base de datos SQLite se crea automáticamente al iniciar por primera vez.

## Capturas de pantalla

*(Agregar capturas de: login, panel principal, lista de usuarios, lista de productos, panel de validación)*

## Historias de usuario implementadas

- **HU-01:** Registro de producto (Ofertante)
- **HU-02:** Edición/Eliminación de producto (Ofertante)
- **HU-03:** Validación de contenido (Administrador)
