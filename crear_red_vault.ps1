$ROOT = "E:\Red"

Write-Host ""
Write-Host "Creando vault en: $ROOT" -ForegroundColor Cyan
Write-Host ""

$carpetas = @(
    "00_sistema",
    "01_leads\activos",
    "01_leads\contactados",
    "01_leads\frios",
    "01_leads\convertidos",
    "02_prototipos\templates",
    "02_prototipos\generados",
    "03_campanas",
    "04_seal_logs",
    "05_social_fallback"
)

foreach ($c in $carpetas) {
    New-Item -ItemType Directory -Path "$ROOT\$c" -Force | Out-Null
}

Set-Content -Path "$ROOT\00_sistema\config.md" -Encoding UTF8 -Value @"
---
type: config
---

# Configuracion global

## Zonas
- Zona A:
- Zona B:

## Categorias de negocio
- restaurante
- tienda
- clinica
- servicios

## Parametros generales
- dias_sin_respuesta_frio: 10
- email_remitente:
- precio_prototipo:
- dominio_base:
"@

Set-Content -Path "$ROOT\00_sistema\README.md" -Encoding UTF8 -Value @"
---
type: doc
---

# RED - Sistema de prospeccion local

## Flujo general
1. Scraping a leads en 01_leads/activos/
2. Email inicial a mover a contactados/
3. Sin respuesta mas de 10 dias a mover a frios/
4. Cierre a mover a convertidos/
"@

Set-Content -Path "$ROOT\01_leads\_plantilla_lead.md" -Encoding UTF8 -Value @"
---
type: lead
estado: activo
nombre:
zona:
categoria:
email:
telefono:
web_actual:
fecha_scraping:
fecha_contacto:
fecha_followup:
prototipo:
notas:
---

# nombre del negocio

## Datos
- Web actual:
- Email:
- Zona:

## Historial
- [ ] Email inicial enviado
- [ ] Followup 1
- [ ] Followup 2

## Notas

"@

Set-Content -Path "$ROOT\02_prototipos\templates\README.md" -Encoding UTF8 -Value @"
# Templates HTML base

restaurante.html  - Restaurantes y bares
tienda.html       - Comercio local
clinica.html      - Salud y estetica
servicios.html    - Servicios profesionales
"@

Set-Content -Path "$ROOT\03_campanas\README.md" -Encoding UTF8 -Value @"
# Campanas

Estructura: YYYY-MM_zona-categoria

Cada campana contiene leads.md y resultados.md
"@

Set-Content -Path "$ROOT\04_seal_logs\README.md" -Encoding UTF8 -Value @"
# SEAL - Logs de aprendizaje

Formato de entrada:
Fecha: YYYY-MM-DD
Campana:
Observacion:
Ajuste propuesto:
"@

Set-Content -Path "$ROOT\05_social_fallback\README.md" -Encoding UTF8 -Value @"
# Social Fallback - Fase 2

Canales previstos:
- WhatsApp Business
- Instagram DM

Estado: estructura lista, pendiente de activar
"@

Write-Host "Vault creado correctamente:" -ForegroundColor Green
Get-ChildItem -Path $ROOT -Recurse | Where-Object { -not $_.PSIsContainer } | ForEach-Object {
    Write-Host "  $($_.FullName.Replace($ROOT, ''))" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Listo. Abre E:\Red como vault en Obsidian." -ForegroundColor Cyan
Write-Host ""
Read-Host "Pulsa Enter para cerrar"