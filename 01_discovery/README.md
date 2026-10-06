# Web Verifier (`web_verifier.py`)

## Descripción
Módulo de la fase de **Discovery** (`01_discovery`) diseñado para verificar, resolver y clasificar la presencia web de los leads en la base de datos local (`red.db`). Determina automáticamente si un negocio posee un sitio web propio funcional, si carece de él, si el dominio está inactivo, o si depende exclusivamente de plataformas de terceros (redes sociales o directorios).

## Funciones Principales

- **Validación de URLs (`verify_lead`)**: 
  - Evalúa la URL asociada a un lead mediante peticiones `HTTP HEAD` ultrarrápidas (`httpx`).
  - Sigue redirecciones para descubrir el dominio de destino real.
  - Actualiza la base de datos local con el nuevo `website_status` y `status`.

- **Clasificación Inteligente (`classify_url`)**: 
  Categoriza las URLs procesadas en 5 estados clave:
  1. `sin_web`: Lead sin página web asignada.
  2. `social` / `directory` (`social_or_directory`): Presencia delegada a plataformas (ej. Facebook, Instagram, TripAdvisor, Yelp, Páginas Amarillas).
  3. `dead`: Dominio expirado, error de servidor o conexión rechazada (Status HTTP >= 400).
  4. `owned`: Dominio corporativo propio y funcional.
  5. `unknown`: Fallos de resolución DNS o timeouts extremos.

- **Procesamiento Masivo (`verify_all_pending`)**: 
  - Recupera todos los leads marcados como `sin_verificar`.
  - Procesa la cola mostrando una barra de progreso interactiva mediante `tqdm`.

- **Soporte de Búsqueda de Respaldo (`google_search`)**:
  - Función de scraping ligero sobre Google para extraer hasta las top 5 URLs a partir de una query, pensada para enriquecer leads sin datos.

## Dependencias

- Python 3.10+
- `httpx` (para peticiones asíncronas / sincronas de red)
- `tqdm` (para seguimiento visual de progreso en terminal)
- `sqlite3` (librería estándar, motor de base de datos local)
- Acceso a `config.py` y configuración base en `E:\RED` (o `D:\Red`).

## Uso

Para lanzar la verificación masiva de todos los leads pendientes de validación, ejecuta el script directamente:

```bash
python web_verifier.py
```

Para integrar la validación atómica en otros módulos, importar la función alias pública:

```python
from web_verifier import classify_url

resultado = classify_url("http://facebook.com/minegocio")
# Devuelve: "social"
```
