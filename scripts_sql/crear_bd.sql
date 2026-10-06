CREATE DATABASE IF NOT EXISTS cariodetector
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE cariodetector;

CREATE TABLE IF NOT EXISTS analisis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_imagen VARCHAR(255) NOT NULL,
    fecha_analisis DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_detecciones INT DEFAULT 0,
    ruta_imagen_original VARCHAR(500),
    ruta_imagen_resultado VARCHAR(500),
    observaciones TEXT
) ENGINE=InnoDB;

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