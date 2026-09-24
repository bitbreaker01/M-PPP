# Playbook: paquete-plugins · sanic_mppp_pkg_plugins

Inventario 8.0/8.1/8.2 dependen de este paquete: sin él no existen los `plugintype`
a los que apuntan las dos Custom API y los 18 steps.

Antes de correr la herramienta hay que armar el .nupkg:

```
dotnet pack src/Sanic.Mppp.Plugins.Paquete/Sanic.Mppp.Plugins.Paquete.csproj -c Release
```

## 1. Identidad

```json
{
  "tipo_playbook": "paquete-plugins",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "8.0",
  "fase": 1,
  "entorno_url": "https://org36e60d9d.crm.dynamics.com/",
  "solucion": "sanic_mppp_sol_mantenimientoppp",
  "publisher": "Sistemas_Abiertos_Nicaragua",
  "prefijo": "sanic",
  "abrev": "mppp",
  "prefijo_opciones": 15946,
  "lcid": 1033
}
```

## 2. Qué se crea

```json
{
  "tipo": "paquete-plugins",
  "nombre": "sanic_mppp_pkg_plugins",
  "uniquename": "sanic_mppp_pkg_plugins",
  "version": "1.0.0",
  "nupkg": "src/Sanic.Mppp.Plugins.Paquete/bin/Release/SanicMpppPlugins.1.0.0.nupkg",
  "tipos": [
    "Sanic.Mppp.Plugins.Api.ClasificarCorreoApi",
    "Sanic.Mppp.Plugins.Api.ValidarSolicitudApi",
    "Sanic.Mppp.Plugins.Steps.ListaBlancaStep",
    "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
    "Sanic.Mppp.Plugins.Steps.NombreCalculadoStep",
    "Sanic.Mppp.Plugins.Steps.IntegridadDeReglaStep",
    "Sanic.Mppp.Plugins.Steps.TransicionDeFilaStep",
    "Sanic.Mppp.Plugins.Steps.PostTransicionDeFilaStep",
    "Sanic.Mppp.Plugins.Steps.AtenderPorClasificarStep"
  ]
}
```

## 3. Precondiciones

- La solución `sanic_mppp_sol_mantenimientoppp` existe, es unmanaged y su publisher es `Sistemas_Abiertos_Nicaragua` (lo comprueba la herramienta).
- El .nupkg está armado y pesa menos de 12 MB. Solo puede llevar `Sanic.Mppp.Plugins.dll` y los dos de `DocumentFormat.OpenXml`: el SDK de Dataverse ya vive en el sandbox y no viaja (`ExcludeAssets="runtime"` en el csproj del paquete).
- Ningún step registrado todavía. Si hubiera steps apuntando a estos tipos, un cambio de `major`/`minor` del ensamblado NO los re-apunta solo (Learn, "Assembly versioning").

## 4. Qué NO hace esta herramienta

- No borra el paquete. Borrarlo se lleva puestos los ensamblados, los tipos y **todos** sus steps.
- No corrige `nombre` ni `version`: son inmutables en el servidor. Si están mal, hay que borrar a mano y rehacer.
- No actualiza el contenido salvo que se lo pidan con `--actualizar-contenido`.
