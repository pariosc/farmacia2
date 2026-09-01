# Guía sencilla para actualizar la base de Farmacia

## ¿Qué archivo debe ejecutar el administrador?

Solo este archivo:

```text
migrations/FARMACIA_ACTUALIZACION_DESDE_ORIGINAL.sql
```

No necesita ejecutar los demás archivos SQL del proyecto.

## ¿Qué hace este archivo?

Actualiza la base original de Farmacia para que pueda trabajar con la versión
nueva del sistema. Agrega:

- tipos de producto;
- precios de venta;
- cálculo de subtotales y totales;
- dispensaciones con receta;
- ventas sin receta;
- reserva temporal de medicamentos;
- confirmación de pagos;
- corrección y anulación de notas;
- consumo interno;
- control de lotes y vencimientos;
- relación correcta entre nota y factura.

No borra las recetas ni las dispensaciones antiguas. Tampoco cambia los datos de
otros módulos.

## Antes de ejecutarlo

1. Hacer una copia de seguridad de la base.
2. Verificar que nadie esté registrando operaciones durante la actualización.
3. Confirmar que el archivo corresponde a la versión actual del proyecto.

## Cómo ejecutarlo

Desde una terminal ubicada en la carpeta del proyecto:

```bash
psql "$DATABASE_URL" -X -f migrations/FARMACIA_ACTUALIZACION_DESDE_ORIGINAL.sql
```

`DATABASE_URL` debe apuntar a la base real del hospital. No escribir la
contraseña dentro del archivo SQL ni enviarla por chat.

## ¿Cómo saber si terminó bien?

Al final debe aparecer un mensaje parecido a:

```text
Farmacia actualizada completamente desde BD original.
```

Si aparece un error, detenerse y guardar todo el mensaje. No volver a ejecutar
varias veces ni borrar tablas para intentar corregirlo.

## Después de actualizar

1. Reiniciar el backend de Farmacia.
2. Revisar que aparezcan productos, lotes y existencias.
3. Definir precios de venta mayores que cero.
4. Probar una dispensación de prueba.
5. Probar una consulta de cobro.
6. Confirmar que el stock no se descuente antes del pago y la entrega.

## Explicación corta para el administrador

> Este archivo toma la base original de Farmacia y le agrega las estructuras
> necesarias para precios, reservas, pagos, dispensación y consumo interno. Es
> un único archivo, trabaja por etapas, se detiene si encuentra un problema y
> no debe ejecutarse sin respaldo.

## Importante sobre otros módulos

La base de Farmacia guarda solamente referencias de Atención, Cobros, Seguridad
e Internación. La información completa de esos módulos se obtiene mediante sus
APIs; no se deben copiar ni modificar sus tablas directamente.
