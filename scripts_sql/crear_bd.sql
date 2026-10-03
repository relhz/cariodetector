-- Script SQL para crear la base de datos y tablas
-- Ejecutar en MySQL: source scripts_sql/crear_bd.sql

CREATE DATABASE IF NOT EXISTS cariodetector
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE cariodetector;

-- Tabla principal de análisis
CREATE TABLE IF NOT EXISTS analisis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_imagen VARCHAR(255) NOT NULL,
    fecha_analisis DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_detecciones INT DEFAULT 0,
    ruta_imagen_original VARCHAR(500),
    ruta_imagen_resultado VARCHAR(500),
    observaciones TEXT
) ENGINE=InnoDB;

-- Tabla de detecciones individuales por análisis
CREATE TABLE IF NOT EXISTS detecciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analisis_id INT NOT NULL,
    clase_id INT NOT NULL,
    nombre_clase VARCHAR(50) NOT NULL,
    confianza DECIMAL(5,4) NOT NULL,
    bbox_x DECIMAL(8,4) NOT NULL,
    bbox_y DECIMAL(8,4) NOT NULL,
    bbox_w DECIMAL(8,4) NOT NULL,
    bbox_h DECIMAL(8,4) NOT NULL,
    FOREIGN KEY (analisis_id) REFERENCES analisis(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Índices para consultas frecuentes
CREATE INDEX idx_analisis_fecha ON analisis(fecha_analisis);
CREATE INDEX idx_detecciones_analisis ON detecciones(analisis_id);
CREATE INDEX idx_detecciones_clase ON detecciones(nombre_clase);

-- Vista para resumen rápido
CREATE OR REPLACE VIEW vista_resumen_analisis AS
SELECT
    a.id,
    a.nombre_imagen,
    a.fecha_analisis,
    a.total_detecciones,
    COUNT(d.id) AS detecciones_guardadas,
    GROUP_CONCAT(CONCAT(d.nombre_clase, ':', COUNT(*)) SEPARATOR ', ') AS resumen_tipos
FROM analisis a
LEFT JOIN detecciones d ON a.id = d.analisis_id
GROUP BY a.id, a.nombre_imagen, a.fecha_analisis, a.total_detecciones;

-- Datos de prueba (opcional, descomente si quiere datos de ejemplo)
-- INSERT INTO analisis (nombre_imagen, total_detecciones, ruta_imagen_original)
-- VALUES ('ejemplo_cromosomas.jpg', 46, 'assets/imagenes/ejemplo_cromosomas.jpg');
-- INSERT INTO detecciones (analisis_id, clase_id, nombre_clase, confianza, bbox_x, bbox_y, bbox_w, bbox_h)
-- VALUES (1, 0, 'cromosoma 1', 0.95, 100, 100, 50, 100),
--        (1, 1, 'cromosoma 2', 0.92, 200, 100, 48, 98);

-- Usuario de aplicación (opcional, ajuste contraseña)
-- CREATE USER IF NOT EXISTS 'cariodetector'@'localhost' IDENTIFIED BY 'password123';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON cariodetector.* TO 'cariodetector'@'localhost';
-- FLUSH PRIVILEGES;