# Modelo de IA: estado actual y verificación de scikit-learn

## 1. Qué pregunta responde el modelo

Para cada turno, el servicio `suggestion-service` necesita saber **cuántos minutos tardará una atención** (por servicio, punto y tipo de paciente). Con eso calcula:

- **Espera de un punto** = tiempo restante del paciente en curso + suma de las duraciones estimadas de quienes van delante.
- **Punto sugerido** = el de menor espera estimada.
- **Espera de cada turno en la fila**, que ven recepción, médico, pantalla y paciente.

## 2. Modelo actual (EMA con contracción)

Implementado en `suggestion-service/app/models/estimator.py`, sin librerías de aprendizaje automático.

1. Guarda, por cada combinación **(servicio, punto, grupo)**, una media móvil de la duración real y el número de muestras. El grupo es `normal` o `pref` (preferencial).
2. Cada nivel se acerca al nivel más general con un prior bayesiano ligero: `est = (n·media + K·padre) / (n + K)`, con `K = 3`.
3. La cadena de niveles es: valor inicial del servicio → (servicio, grupo) → (servicio, punto) → (servicio, punto, grupo).
4. El peso de cada media se limita a 50 muestras para que el modelo siga adaptándose si el comportamiento cambia.

Ventajas: arranca bien sin datos, aprende desde la primera atención, es explicable, no requiere entrenamiento por lotes y consume memoria despreciable.

### 2.1 Medición de efectividad (pantalla "Prueba del modelo")

Cada vez que una atención finaliza, `turnos-api` llama a `/learn` con la duración real y el valor inicial del servicio. Antes de aprender, el servicio registra en `TrainingLog` lo que el modelo **habría predicho** (evaluación honesta, *prequential*) junto con el error de la línea base (solo el valor inicial). Con eso el supervisor ve:

| Métrica | Significado |
|---|---|
| Error del modelo (MAE) | Diferencia media absoluta entre minutos predichos y reales |
| Error sin IA | Lo mismo usando solo el valor inicial del servicio |
| Mejora | `1 − MAE / MAE base` |
| Aciertos ±3 min | % de predicciones a 3 minutos o menos de la realidad |
| Curva de aprendizaje | Error medio móvil (10 atenciones) del modelo frente a la línea base |
| Madurez por punto | Muestras / 20 por servicio, punto y tipo de paciente |

También puede **consultarse al modelo** (`POST /api/model/predict`): devuelve duración estimada con rango probable, confianza, desglose del cálculo por nivel y a qué punto enviaría hoy a un paciente normal o preferencial.

### 2.2 Atención prioritaria

El modelo no solo estima duraciones: decide cuánta prioridad conceder. Para un paciente preferencial calcula la espera en cada punto con el adelanto mínimo (20 min) y lo incrementa de 5 en 5 hasta cumplir la meta de espera (10 min) o llegar al tope (60 min). Se reporta el ahorro frente a un turno normal. Los parámetros se configuran con `PRIORITY_TARGET_WAIT_MIN`, `PRIORITY_BASE_BONUS_MIN` y `PRIORITY_MAX_BONUS_MIN`.

## 3. Verificación de scikit-learn

**Pregunta:** ¿se puede implementar scikit-learn en el microservicio?

**Respuesta corta: sí, es técnicamente viable. Hoy no aporta una mejora que justifique su costo.**

### 3.1 Método

Script reproducible: `suggestion-service/experiments/sklearn_feasibility.py`. Genera un flujo sintético de 1500 atenciones con ruido (log-normal), efecto de edad, hora del día y prioridad, y un **cambio de comportamiento** en el evento 750 (el Consultorio 2 se vuelve más rápido). Se evalúa con el método *prequential*: cada atención se predice **antes** de aprender de ella.

Modelos comparados:

- Solo valor inicial (sin aprender).
- EMA con contracción (el actual).
- scikit-learn **Ridge** (regresión lineal regularizada) con codificación one-hot de servicio y punto, más edad, hora y prioridad.
- scikit-learn **GradientBoosting** (árboles), con todo el historial y con ventana de las últimas 300 muestras.

Los datos son **sintéticos**: sirven para comparar enfoques y costos, no para afirmar la precisión real en una clínica.

### 3.2 Compatibilidad (verificada)

| Entorno | Resultado |
|---|---|
| Docker `python:3.12-slim`, x86-64 (equipo de desarrollo) | scikit-learn 1.9.1 instala y funciona |
| Docker `python:3.12-slim`, **aarch64 (Raspberry Pi de producción)** | scikit-learn 1.9.1 instala y funciona (hay ruedas precompiladas, no compila) |

### 3.3 Precisión (MAE en minutos, menor es mejor)

Cada columna es un tramo del flujo de atenciones; el cambio de comportamiento ocurre al iniciar el tramo 750–900.

| Modelo | 0–50 | 50–150 | 150–400 | 400–750 | 750–900 | 900–1500 |
|---|---|---|---|---|---|---|
| Solo valor inicial | 4.23 | 4.40 | 4.80 | 4.57 | 3.82 | 3.18 |
| **EMA + contracción (actual)** | 3.99 | 3.05 | 3.20 | 3.33 | 3.95 | 3.00 |
| sklearn Ridge (todo el historial) | 4.23 | 2.73 | 3.11 | 3.33 | 3.89 | 3.04 |
| sklearn GradientBoosting (todo) | 4.23 | 3.55 | 3.48 | 3.59 | 3.91 | 2.99 |
| sklearn GradientBoosting (últ. 300) | 4.23 | 3.55 | 3.51 | 3.60 | 3.73 | **2.64** |

Lectura:

- Con pocos datos (primeras 50 atenciones) scikit-learn **no puede predecir**: en el experimento se reentrena cada 25 atenciones a partir de 30, así que el primer modelo aparece en la atención 50. Hasta entonces usa el valor inicial. El EMA ya mejora desde la primera atención.
- Ridge supera al EMA entre 50 y 150 atenciones (2.73 vs 3.05) y luego empatan.
- Tras el cambio de comportamiento, solo GradientBoosting con ventana corta supera al EMA (2.64 vs 3.00, ≈ 12 % menos error) y únicamente en el último tramo.
- El ruido propio de los datos limita el mínimo alcanzable: hay poco margen de mejora sobre el EMA.

### 3.4 Costo operativo

| Métrica | EMA (actual) | scikit-learn |
|---|---|---|
| Tamaño de dependencias (site-packages) | ≈ 94–100 MB | ≈ 355–377 MB (**+ ≈ 260–275 MB** de imagen) |
| Memoria adicional al importar | ≈ 0 | **+ ≈ 95–99 MB** |
| Predicción (x86-64 / Raspberry Pi) | 0.3 / 1.4 ms (incluye consulta SQL) | Ridge 3.3 / 5.8 ms · GradientBoosting 3.9 / 6.6 ms |
| Entrenamiento (≤ 1500 filas, x86-64 / Raspberry Pi) | no requiere | Ridge 20–30 ms · GradientBoosting 210 / 563 ms |
| Arranque (import) | inmediato | 0.1–0.5 s |

En una Raspberry Pi de 4 GB que ya aloja otros servicios, ≈ 100 MB de RAM y ≈ 270 MB de imagen adicionales son asumibles, pero no gratuitos.

## 4. Conclusión y recomendación

1. **Mantener el EMA como modelo por defecto.** Aprende desde la primera muestra, es explicable y barato.
2. **scikit-learn es viable** cuando haya motivo. Se recomienda evaluarlo cuando se cumplan **ambas** condiciones:
   - exista un volumen real de atenciones finalizadas (orden de **≥ 500**), y
   - se compruebe con datos reales que variables como **edad, hora del día o tamaño de la fila** explican la duración (en los datos sintéticos el beneficio es modesto).
3. **Diseño de integración propuesto** (si se decide hacerlo):
   - Añadir un `SklearnEstimator` en `models/` con la misma interfaz que el actual (`estimate`, `learn`) y elegirlo por variable de entorno (`ESTIMATOR=ema|sklearn`).
   - Entrenar de forma periódica (no en cada petición) con una ventana de las últimas ~300–500 atenciones, y persistir el modelo con `joblib`.
   - **Respaldo:** mientras haya menos de ~30 muestras, o si falla la carga del modelo, usar el EMA.
   - Guardar las atenciones individuales (hoy solo se guardan medias) para poder entrenar: requiere una tabla nueva en `turi_suggest`.
4. Alternativa de menor costo: añadir al EMA un factor por hora del día. Captura parte de la señal sin dependencias nuevas.

## 5. Cómo reproducir

```bash
cd suggestion-service
pip install -r requirements.txt scikit-learn
python experiments/sklearn_feasibility.py
```
