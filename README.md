# OULAD Data Analytics Pipeline

Este repositorio contiene el pipeline de Ingeniería de Datos y Analítica Avanzada para el dataset **OULAD (Open University Learning Analytics dataset)**. El objetivo del proyecto es estructurar, limpiar e integrar los datos en un entorno relacional, aplicar ingeniería de características (transformaciones ordinales) y realizar un Análisis Exploratorio de Datos (EDA) extendido.

---

## 📘 Diccionario de Datos del Proyecto

| Tabla | Columna | Tipo de Llave / Restricción | Descripción Técnica del Campo |
| :--- | :--- | :--- | :--- |
| **courses** | `code_module` | Clave Primaria (Compuesta 1/2) | Código de identificación asignado a la materia (ej. AAA, BBB). |
| **courses** | `code_presentation` | Clave Primaria (Compuesta 2/2) | Código del semestre. Termina en 'B' (inicio Febrero) o 'J' (inicio Octubre). |
| **courses** | `length` | Atributo | Duración total del curso expresada en días cronológicos. |
| **studentInfo** | `code_module` | PK Compuesta / Llave Foránea | Enlace con la tabla catálogo de `courses`. |
| **studentInfo** | `code_presentation` | PK Compuesta / Llave Foránea | Enlace con la tabla catálogo de `courses`. |
| **studentInfo** | `id_student` | Clave Primaria (Compuesta 3/3) | Identificador único y aleatorizado del estudiante. |
| **studentInfo** | `gender` | Atributo Categoría | Género del estudiante (M / F). |
| **studentInfo** | `region` | Atributo Categoría | Región geográfica donde reside el estudiante. |
| **studentInfo** | `highest_education` | Atributo Ordinal | Nivel máximo de escolaridad alcanzado al ingresar al curso. |
| **studentInfo** | `imd_band` | Atributo Ordinal / Cuarentena | Índice de Privación Múltiple (Nivel socioeconómico de la zona en percentiles). |
| **studentInfo** | `age_band` | Atributo Ordinal | Rango de edad del alumno (0-35, 35-55, >55). |
| **studentInfo** | `num_of_prev_attempts` | Atributo Numérico | Veces que el alumno ha reprobado o intentado cursar esta misma materia. |
| **studentInfo** | `studied_credits` | Atributo Numérico | Total de créditos académicos que el alumno está cursando en paralelo. |
| **studentInfo** | `disability` | Atributo Categoría | Indica si el estudiante ha declarado alguna discapacidad (Y / N). |
| **studentInfo** | `final_result` | **Variable Objetivo (Label)** | Calificación o estado final en el curso (Pass, Distinction, Fail, Withdrawn). |
| **studentRegistration** | `code_module` | PK Compuesta / Llave Foránea | Conexión compuesta hacia el perfil de `studentInfo`. |
| **studentRegistration** | `code_presentation` | PK Compuesta / Llave Foránea | Conexión compuesta hacia el perfil de `studentInfo`. |
| **studentRegistration** | `id_student` | PK Compuesta / Llave Foránea | Conexión compuesta hacia el perfil de `studentInfo`. |
| **studentRegistration** | `date_registration` | Atributo Numérico | Día relativo de inscripción (valores negativos significan antes del inicio del curso). |
| **studentRegistration** | `date_unregistration` | Atributo Numérico / Control Nulos | Día relativo en que el alumno abandonó. Vacío significa que terminó el curso. |
| **assessments** | `id_assessment` | Clave Primaria | Identificador único de la tarea, cuestionario o examen. |
| **assessments** | `code_module` | Llave Foránea | Código de la materia a la que pertenece la evaluación. |
| **assessments** | `code_presentation` | Llave Foránea | Semestre al que pertenece la evaluación. |
| **assessments** | `assessment_type` | Atributo Categoría | Tipo de evaluación: TMA (Humana), CMA (Computadora), o Exam (Examen Final). |
| **assessments** | `date` | Atributo Numérico | Día límite de entrega (cut-off day) relativo al inicio del semestre. |
| **assessments** | `weight` | Atributo Numérico | Peso o porcentaje de la nota sobre la calificación final del bloque (0 a 100%). |
| **studentAssessment** | `id_assessment` | PK Compuesta / Llave Foránea | Enlace directo con el calendario de la evaluación en `assessments`. |
| **studentAssessment** | `id_student` | PK Compuesta / Llave Foránea | Enlace con el perfil demográfico del estudiante en `studentInfo`. |
| **studentAssessment** | `date_submitted` | Atributo Numérico | Día real en el que el estudiante hizo la entrega de la asignación. |
| **studentAssessment** | `is_banked` | Atributo Binario (0 / 1) | Indica si la nota fue convalidada o transferida desde un semestre anterior. |
| **studentAssessment** | `score` | Atributo Numérico | Nota obtenida de 0 a 100 (Puntajes menores a 40 reflejan reprobación). |
| **vle** | `id_site` | Clave Primaria | Identificador único del recurso digital dentro de la plataforma virtual. |
| **vle** | `code_module` | Llave Foránea | Código de la materia asociada al recurso digital. |
| **vle** | `code_presentation` | Llave Foránea | Código del semestre asociado al recurso digital. |
| **vle** | `activity_type` | Atributo Categoría | Formato del material web (ej. forumng, homepage, oucontent, subpage). |
| **vle** | `week_from` | Atributo Numérico | Semana sugerida para iniciar el uso del material. |
| **vle** | `week_to` | Atributo Numérico | Semana sugerida para finalizar el uso del material. |
| **studentVle** | `code_module` | Llave Foránea | Componente de conexión hacia el estudiante en `studentInfo`. |
| **studentVle** | `code_presentation` | Llave Foránea | Componente de conexión hacia el estudiante en `studentInfo`. |
| **studentVle** | `id_student` | Llave Foránea | Componente de conexión hacia el estudiante en `studentInfo`. |
| **studentVle** | `id_site` | Llave Foránea | Identificador del recurso clickeado. Conecta con la tabla `vle`. |
| **studentVle** | `date` | Atributo Numérico | Día de la interacción relativo al inicio del curso. |
| **studentVle** | `sum_click` | Atributo Numérico (Métrica) | Cantidad de clicks específicos realizados por el alumno en ese recurso ese día. |

---
