CREATE DATABASE IF NOT EXISTS oulad;
USE oulad;

-- Desactivar revisiones temporalmente para que no se tranque la creación por el orden
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS studentVle;
DROP TABLE IF EXISTS studentAssessment;
DROP TABLE IF EXISTS studentRegistration;
DROP TABLE IF EXISTS studentInfo;
DROP TABLE IF EXISTS vle;
DROP TABLE IF EXISTS assessments;
DROP TABLE IF EXISTS courses;

-- 1. Tablas Catálogo (Dimensiones)
CREATE TABLE courses (
    code_module VARCHAR(20),
    code_presentation VARCHAR(20),
    module_presentation_length INT,
    PRIMARY KEY (code_module, code_presentation)
);

CREATE TABLE assessments (
    code_module VARCHAR(20),
    code_presentation VARCHAR(20),
    id_assessment INT,
    assessment_type VARCHAR(20),
    date INT,
    weight DECIMAL(5,2),
    PRIMARY KEY (id_assessment)
);

CREATE TABLE vle (
    id_site INT,
    code_module VARCHAR(20),
    code_presentation VARCHAR(20),
    activity_type VARCHAR(50),
    week_from INT,
    week_to INT,
    PRIMARY KEY (id_site)
);

-- 2. Tabla Perfil de Estudiantes
CREATE TABLE studentInfo (
    code_module VARCHAR(20),
    code_presentation VARCHAR(20),
    id_student INT,
    gender VARCHAR(5),
    region VARCHAR(100),
    highest_education VARCHAR(100),
    imd_band VARCHAR(50), 
    age_band VARCHAR(50),
    num_of_prev_attempts INT,
    studied_credits INT,
    disability VARCHAR(5),
    final_result VARCHAR(50),
    PRIMARY KEY (code_module, code_presentation, id_student)
);

-- 3. Tablas Transaccionales (Hechos)
CREATE TABLE studentRegistration (
    code_module VARCHAR(20),
    code_presentation VARCHAR(20),
    id_student INT,
    date_registration INT,
    date_unregistration INT,
    PRIMARY KEY (code_module, code_presentation, id_student)
);

CREATE TABLE studentAssessment (
    id_assessment INT,
    id_student INT,
    date_submitted INT,
    is_banked INT,
    score INT,
    PRIMARY KEY (id_assessment, id_student)
);

CREATE TABLE studentVle (
    code_module VARCHAR(20),
    code_presentation VARCHAR(20),
    id_student INT,
    id_site INT,
    date INT,
    sum_click INT
);

SET FOREIGN_KEY_CHECKS = 1;


-- Prueba de Insersion de Datos desde Python

SELECT COUNT(*) FROM studentInfo;

SELECT * FROM studentvle
Limit 1000;

SELECT table_name, table_rows 
FROM information_schema.tables 
WHERE table_schema = 'oulad' AND table_name = 'studentVle';

-- Creacion de llaves luego de limpieza de Datos

-- ======================================================================
-- ESTRUCTURACIÓN RELACIONAL RESTRICCIONES (PK Y FK) - ESQUEMA OULAD
-- ======================================================================

-- PASO 1: DECLARACIÓN DE LLAVES PRIMARIAS (PRIMARY KEYS)
-- ALTER TABLE courses ADD PRIMARY KEY (code_module, code_presentation);
ALTER TABLE courses MODIFY code_module VARCHAR(50), MODIFY code_presentation VARCHAR(50);
ALTER TABLE courses ADD PRIMARY KEY (code_module, code_presentation);
ALTER TABLE assessments ADD PRIMARY KEY (id_assessment);
ALTER TABLE vle ADD PRIMARY KEY (id_site);
-- ALTER TABLE studentInfo ADD PRIMARY KEY (code_module, code_presentation, id_student);
ALTER TABLE studentInfo MODIFY code_module VARCHAR(50), MODIFY code_presentation VARCHAR(50);
ALTER TABLE studentInfo ADD PRIMARY KEY (code_module, code_presentation, id_student);
-- ALTER TABLE studentRegistration ADD PRIMARY KEY (code_module, code_presentation, id_student);
ALTER TABLE studentRegistration MODIFY code_module VARCHAR(50), MODIFY code_presentation VARCHAR(50);
ALTER TABLE studentRegistration ADD PRIMARY KEY (code_module, code_presentation, id_student);
ALTER TABLE studentAssessment ADD PRIMARY KEY (id_assessment, id_student);

-- ======================================================================
-- PASO 2: DECLARACIÓN DE LLAVES FORÁNEAS (FOREIGN KEYS) Y CARDINALIDADES
-- ======================================================================

-- ======================================================================
-- ESTANDARIZACIÓN DE TIPOS DE DATOS RESTANTES (TEXT a VARCHAR)
-- ======================================================================
ALTER TABLE assessments MODIFY code_module VARCHAR(50), MODIFY code_presentation VARCHAR(50);
ALTER TABLE vle MODIFY code_module VARCHAR(50), MODIFY code_presentation VARCHAR(50);

-- Relación Uno a Muchos (1:N): Un curso oferta múltiples evaluaciones independientes.
ALTER TABLE assessments 
ADD CONSTRAINT fk_assessments_courses 
FOREIGN KEY (code_module, code_presentation) REFERENCES courses(code_module, code_presentation) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- Relación Uno a Muchos (1:N): Un curso aloja múltiples recursos virtuales (vle) en la plataforma.
ALTER TABLE vle 
ADD CONSTRAINT fk_vle_courses 
FOREIGN KEY (code_module, code_presentation) REFERENCES courses(code_module, code_presentation) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- Relación Uno a Muchos (1:N): Un curso recibe la inscripción de múltiples estudiantes (perfil demográfico).
ALTER TABLE studentInfo 
ADD CONSTRAINT fk_studentInfo_courses 
FOREIGN KEY (code_module, code_presentation) REFERENCES courses(code_module, code_presentation) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- Relación Uno a Uno (1:1): Correspondencia exclusiva entre la matrícula del alumno y su perfil demográfico por curso.
ALTER TABLE studentRegistration 
ADD CONSTRAINT fk_registration_student 
FOREIGN KEY (code_module, code_presentation, id_student) REFERENCES studentInfo(code_module, code_presentation, id_student) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- Relación Uno a Muchos (1:N): Una evaluación del catálogo recibe las calificaciones de múltiples estudiantes.
ALTER TABLE studentAssessment 
ADD CONSTRAINT fk_studentAssessment_assessments 
FOREIGN KEY (id_assessment) REFERENCES assessments(id_assessment) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- Homologo  tipos de datos (id_site)

ALTER TABLE vle MODIFY id_site BIGINT;
ALTER TABLE studentVle MODIFY id_site BIGINT;

-- Aprovecho para asegurar que id_student sea del mismo tipo en ambas tablas
ALTER TABLE studentInfo MODIFY id_student BIGINT;
ALTER TABLE studentVle MODIFY id_student BIGINT;

-- Relación Uno a Muchos (1:N): Un recurso didáctico (sitio) registra múltiples clicks en la bitácora transaccional.
ALTER TABLE studentVle 
ADD CONSTRAINT fk_studentVle_vle 
FOREIGN KEY (id_site) REFERENCES vle(id_site) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- Relación Uno a Muchos (1:N): El perfil activo de un estudiante genera múltiples interacciones en la bitácora de clicks.
ALTER TABLE studentVle 
ADD CONSTRAINT fk_studentVle_student 
FOREIGN KEY (code_module, code_presentation, id_student) REFERENCES studentInfo(code_module, code_presentation, id_student) 
ON DELETE CASCADE ON UPDATE CASCADE;


-- ======================================================================
-- VALIDACIÓN DE TABLA student_analytics
-- ======================================================================

SELECT 
    -- 1. Llaves desde nueva tabla student_analytics (Nombrada como analytics)
    analytics.id_student AS Estudiante_ID,
    analytics.code_module AS Modulo,
    analytics.code_presentation AS Semestre,
    
    -- 2. Columnas de texto originales vs Sus nuevos valores ordinales numéricos
    analytics.final_result AS Resultado_Texto,
    analytics.final_result_ordinal AS Resultado_Ordinal_ML,
    
    analytics.highest_education AS Educacion_Texto,
    analytics.education_ordinal AS Educacion_Ordinal_ML,
    
    -- 3. Métrica real traída desde la tabla de calificaciones mediante el JOIN (Nombrada como notas)
    notas.id_assessment AS Evaluacion_ID,
    notas.score AS Calificacion_Obtenida

FROM student_analytics AS analytics
-- Relaciono usando el ID único del estudiante
INNER JOIN studentAssessment AS notas 
   ON analytics.id_student = notas.id_student
LIMIT 50;


-- ----------------------------------------------------------------------
-- TABLÓN MAESTRO DE EVALUACIONES (v_full_domain_assess)
-- Fusión completa de catálogo de exámenes y notas de alumnos
-- ----------------------------------------------------------------------
CREATE OR REPLACE VIEW v_full_domain_assess AS
SELECT 
    -- Todo de studentAssessment
    sa.id_student,
    sa.id_assessment,
    sa.date_submitted,
    sa.is_banked,
    sa.score,
    
    -- Todo de assessments (excepto id_assessment que ya se incluyó)
    a.code_module,
    a.code_presentation,
    a.assessment_type,
    a.date AS date_planned,
    a.weight

FROM studentAssessment sa
INNER JOIN assessments a ON sa.id_assessment = a.id_assessment;

-- ----------------------------------------------------------------------
-- TABLÓN MAESTRO DE RECURSOS VIRTUALES (v_full_domain_vle)
-- Fusión completa de la bitácora de clicks y catálogo de recursos
-- ----------------------------------------------------------------------
CREATE OR REPLACE VIEW v_full_domain_vle AS
SELECT 
    -- Todo de studentVle
    sv.code_module,
    sv.code_presentation,
    sv.id_student,
    sv.id_site,
    sv.date,
    sv.sum_click,
    
    -- Todo de vle (excepto las llaves redundantes)
    v.activity_type,
    v.week_from,
    v.week_to

FROM studentVle sv
INNER JOIN vle v ON sv.id_site = v.id_site;

SELECT * FROM v_full_domain_assess;
SELECT * 
FROM v_full_domain_vle
LIMIT 100;

SELECT *
FROM tablon_investigacion_oulad
LIMIT 100;


