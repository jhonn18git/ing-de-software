# SmartSchedule — Especificaciones SDD

## Sprint 1: Gestión de Usuarios

### SPEC: AUTH-01 - Login exitoso con credenciales válidas
- Input: { username: "admin", password: "admin123" }
- Expected: 200 OK, sesión iniciada, datos del usuario sin contraseña
- Endpoint: POST /api/auth/login

### SPEC: AUTH-02 - Login fallido con credenciales incorrectas
- Input: { username: "admin", password: "wrong" }
- Expected: 401 Unauthorized, mensaje de error

### SPEC: AUTH-03 - Logout destruye la sesión
- Expected: 200 OK, cookie de sesión eliminada

### SPEC: AUTH-04 - /me devuelve usuario autenticado
- Expected: 200 OK con datos del usuario actual
- Si no autenticado: 401 Unauthorized

### SPEC: USR-01 - Solo admin puede listar todos los usuarios
- GET /api/users con rol admin → 200 OK, lista de usuarios
- GET /api/users con rol demandante → 403 Forbidden

### SPEC: USR-02 - Creación de usuario requiere campos obligatorios
- Input: { name, username, email, password }
- Si falta alguno → 400 Bad Request

### SPEC: USR-03 - No se pueden crear usuarios con username/email duplicado
- Expected: 409 Conflict

### SPEC: USR-04 - Solo admin puede eliminar usuarios
- DELETE /api/users/:id con rol admin → 200 OK
- Admin no puede eliminar su propia cuenta → 400

## Sprint 2: Gestión de Productos

### SPEC: HU-01 - Registro exitoso de producto con estado pendiente
- Input: { title, description, price, category }
- Expected: 201 Created, status = "pendiente"
- Endpoint: POST /api/products

### SPEC: HU-01 - Rechazo si faltan campos obligatorios
- Input: { title: "test" } (faltan description, price, category)
- Expected: 400 Bad Request

### SPEC: HU-02 - Edición de producto vuelve estado a pendiente
- PUT /api/products/:id con cualquier cambio
- Expected: status = "pendiente" independientemente del estado anterior
- Endpoint: PUT /api/products/:id

### SPEC: HU-02 - Ofertante no puede editar productos de otro ofertante
- Expected: 403 Forbidden

### SPEC: HU-03 - Admin puede aprobar producto pendiente
- PATCH /api/products/:id/status { status: "aprobado" }
- Expected: 200 OK, product.status = "aprobado"

### SPEC: HU-03 - Admin puede rechazar producto pendiente
- PATCH /api/products/:id/status { status: "rechazado" }
- Expected: 200 OK, product.status = "rechazado"

### SPEC: HU-03 - Admin no puede aprobar producto ya aprobado (idempotencia)
- Si product.status ya es "aprobado" y se envía { status: "aprobado" }
- Expected: 200 OK con mensaje "El producto ya está en estado 'aprobado'"

### SPEC: VIS-01 - Demandante solo ve productos aprobados
- GET /api/products con rol demandante
- Expected: solo productos con status = "aprobado"

### SPEC: VIS-02 - Ofertante solo ve sus propios productos
- GET /api/products con rol ofertante
- Expected: solo productos donde ofertante_id = session.user.id
