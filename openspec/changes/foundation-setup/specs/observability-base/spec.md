## ADDED Requirements

### Requirement: Logging estructurado en JSON

El sistema SHALL emitir sus logs en formato estructurado JSON en una sola línea por evento, de modo que sean parseables por agregadores de logs. Cada registro SHALL incluir, como mínimo, timestamp, nivel y mensaje. Los logs NO SHALL contener secretos ni PII en texto plano.

#### Scenario: Formato de log parseable

- **WHEN** la aplicación emite un log durante su operación
- **THEN** la salida es una línea JSON válida con campos de timestamp, nivel y mensaje

### Requirement: Instrumentación OpenTelemetry inicial

El sistema SHALL instrumentar la aplicación FastAPI con OpenTelemetry para trazas, de forma que cada request HTTP genere un span asociado. La instrumentación SHALL ser configurable por entorno (p. ej. activable/desactivable y con destino de exportación parametrizable), sin acoplar el arranque a un backend de telemetría específico.

#### Scenario: Request genera un span

- **WHEN** llega una request HTTP a la aplicación con la instrumentación activada
- **THEN** se genera un span de OpenTelemetry que representa esa request

#### Scenario: Telemetría no bloquea el arranque

- **WHEN** la aplicación inicia sin un backend de exportación de telemetría configurado
- **THEN** la app arranca normalmente y sirve requests sin fallar por la ausencia del exporter
