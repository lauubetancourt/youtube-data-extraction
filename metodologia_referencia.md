### metodologia_referencia.md

### Xiao et al. (2025) - Detección Basada en MACD
*   **Fórmulas Matemáticas y Lógica de Disparo:**
    *   **Media Móvil Exponencial (EMA):**
        $$EMA_n(t) = \sum_{k=0}^{n} \alpha(1-\alpha)^k x(t-k)$$
        Donde $\alpha = 2/(n+1)$.
    *   **Indicadores de Tendencia:**
        $$DIF(t) = EMA_{12}(t) - EMA_{26}(t)$$
        $$DEA(t) = \text{Promedio móvil de 9 días del DIF}$$
        $$MACD(t) = (DIF(t) - DEA(t)) \times 2$$
    *   **Ratio de Intensidad (K):**
        $$Histogram_{fast} = \frac{\sum_{i=0}^{24} |Histogram_i|}{24}$$
        $$Histogram_{slow} = \frac{\sum_{i=0}^{720} |Histogram_i|}{720}$$
        $$K = \frac{Histogram_{fast}}{Histogram_{slow}}$$
    *   **Triggers:**
        *   Activación de ventana: $EMA_{12}(t) > 2 \times \overline{EMA_{12}}_{180d}$.
        *   Inicio de inundación: $K > 2$.
        *   Fin de inundación: $K < 1$.

*   **Arquitectura de Ventanas:**
    *   Ventanas adaptativas basadas en señales de activación.
    *   Granularidad base: 1 hora.
    *   Fusión de ventanas: Si el intervalo entre ellas es < 3 días (ventanas de detección) o < 5 días (eventos detectados).

*   **Tratamiento de Datos:**
    *   **Corrección día/noche:** Exclusión de datos de 8 p.m. a 8 a.m. (ajuste de $n=24$ a $n=12$ en fórmulas).
    *   **Filtrado Geográfico:** Uso de la librería CPCA para mapear (Provincia, Ciudad, Distrito).

*   **Gestión de Estado:**
    *   Buffer histórico de 180 días para el cálculo de $\overline{EMA_{12}}$.
    *   Buffer de 30 días para $Histogram_{slow}$.

### Zhu et al. (2018) - Algoritmo FBTD
*   **Fórmulas Matemáticas y Lógica de Disparo:**
    *   **Suavizado Exponencial Secundario:**
        $$S_t^{(1)} = \alpha v_t + (1-\alpha) S_{t-1}^{(1)}$$
        $$S_t^{(2)} = \alpha S_t^{(1)} + (1-\alpha) S_{t-1}^{(2)}$$
    *   **Cálculo de Aceleración (Trigger de brote):**
        $$A_i = \frac{v_i^p + v_i^{(-1)} - 2 \times v_i^{(0)}}{\Delta T^2}$$
    *   **Umbral Adaptativo:**
        $$\eta_{burst}(t) = Mean[X] + \kappa \times MD[X] \times \frac{Mean[X]}{Mean[X] + MD[X]}$$

*   **Arquitectura de Ventanas:**
    *   Ventana de tiempo deslizante (*Sliding Time Window*).
    *   Tamaño del slot ($\Delta T$): 5 a 10 segundos.

*   **Gestión de Estado:**
    *   Tabla de valores suavizados $S_v$ (recurrente) para minimizar almacenamiento.
    *   Matriz de co-ocurrencia de términos $n \times m^2$ y vector de aceleración $N \times n \times m$.

### Kilroy et al. (2020) - Subdivisión Temporal
*   **Fórmulas Matemáticas y Lógica de Disparo:**
    *   **Z-scoring para ráfagas:** Comparación de frecuencia actual vs. ventanas anteriores.
    *   **Factor de impulso POS:** Multiplicador de $2.5$ para Sustantivos y Nombres Propios.
    *   **Importancia del Evento:** Suma de importancia de términos dividida por el conteo total de términos.

*   **Arquitectura de Ventanas:**
    *   Ventana completa (estática) subdividida en $n$ bloques menores.

*   **Lógica de Subdivisión:**
    *   Divisores de 60: $n \in \{2, 3, 4, 5, 6, 10, 12, 15\}$.

*   **Tratamiento de Datos:**
    *   Filtrado agresivo: Documentos con menos de 4 términos son descartados.
    *   Normalización: Frecuencia de la ventana dividida por la frecuencia total del término.

### Sahin et al. (2019) - Algoritmo Híbrido Storm
*   **Fórmulas Matemáticas y Lógica de Disparo:**
    *   **Tasa de Crecimiento de Clúster (Trigger):**
        $$GR = \frac{\text{Tweets añadidos en la ronda}}{\text{Total de tweets en el clúster}}$$
    *   **Similitud:** Similitud de coseno entre vectores de términos con umbral predefinido.

*   **Arquitectura de Ventanas:**
    *   Procesamiento basado en lotes (*Rounds*).
    *   Tamaño de la ronda: 6 minutos.

*   **Gestión de Estado:**
    *   **Persistencia:** Apache Cassandra para guardar $tf$ de palabras y vectores de clústeres al final de cada ronda.
    *   **Clústeres Locales vs. Globales:** Los clústeres se fusionan localmente por ronda antes de integrarse al estado global.
    *   **Estrategia de limpieza:** Eliminación de clústeres inactivos por más de 2 rondas consecutivas.

### Widanage et al. (2019) - HTM en Indy500
*   **Fórmulas Matemáticas y Lógica de Disparo:**
    *   **Error de Predicción ($S_t$):**
        $$S_t = 1 - \frac{\pi(x_{t-1}) \cdot \alpha(x_t)}{|\alpha(x_t)|}$$
    *   **Trigger:** Puntuación de anomalía basada en el logaritmo de la verosimilitud (distribución normal en ventana previa).

*   **Arquitectura de Ventanas:**
    *   Procesamiento nativo por registro (*tuple-wise*).
    *   Tasa de llegada: 80-90 ms por registro.

*   **Tratamiento de Datos:**
    *   Protocolo MQTT (QoS) y Apache Apollo para gestión de ráfagas.
    *   Configuración TCP_NODELAY para reducir latencia en el transporte de telemetría.

### Weiler et al. (2019) - Simulación Twistor
*   **Fórmulas Matemáticas y Lógica de Disparo:**
    *   **Shifty:** Detecta cambios anómalos en la frecuencia IDF de términos mediante ventana deslizante.
    *   **Log-Likelihood Ratio (LLH):** Diferencia del ratio de verosimilitud de términos entre ventanas subsiguientes.

*   **Arquitectura de Ventanas:**
    *   Configuraciones evaluadas: 5, 10, 15 y 20 minutos.

*   **Gestión de Estado:**
    *   Mantenimiento de la distribución estadística de términos capturada en ventanas de 1 minuto sobre un periodo de 24 horas.