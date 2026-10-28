CREATE DATABASE IF NOT EXISTS `cariotipos`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE `cariotipos`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Tablas
CREATE TABLE IF NOT EXISTS `estudios` (
  `id_estudio` int NOT NULL AUTO_INCREMENT,
  `imagen_original` varchar(255) NOT NULL,
  `cantidad_cromosomas` int DEFAULT NULL,
  `imagen_resultado` varchar(255) DEFAULT NULL,
  `observaciones` text,
  `fecha_analisis` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_estudio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `cromosomas` (
  `id_cromosoma` int NOT NULL AUTO_INCREMENT,
  `id_estudio` int NOT NULL,
  `clase_detectada` varchar(50) DEFAULT NULL,
  `x` int DEFAULT NULL,
  `y` int DEFAULT NULL,
  `ancho` int DEFAULT NULL,
  `alto` int DEFAULT NULL,
  `confianza` decimal(5,4) DEFAULT NULL,
  PRIMARY KEY (`id_cromosoma`),
  KEY `id_estudio` (`id_estudio`),
  CONSTRAINT `cromosomas_ibfk_1` FOREIGN KEY (`id_estudio`) REFERENCES `estudios` (`id_estudio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `clasificaciones` (
  `id_cromosoma` int NOT NULL,
  `cromosoma_asignado` varchar(5) DEFAULT NULL,
  `confianza` decimal(5,4) DEFAULT NULL,
  PRIMARY KEY (`id_cromosoma`),
  CONSTRAINT `fk_clasificaciones_cromosomas` FOREIGN KEY (`id_cromosoma`) REFERENCES `cromosomas` (`id_cromosoma`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `resultados` (
  `id_estudio` int NOT NULL,
  `cariotipo` varchar(30) DEFAULT NULL,
  `alteracion` varchar(100) DEFAULT NULL,
  `observacion` text,
  PRIMARY KEY (`id_estudio`),
  CONSTRAINT `fk_resultados_estudios` FOREIGN KEY (`id_estudio`) REFERENCES `estudios` (`id_estudio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- UDFs para indicadores estadísticos
DROP FUNCTION IF EXISTS `fn_total_estudios`;
DELIMITER $$
CREATE FUNCTION `fn_total_estudios`() RETURNS int
    READS SQL DATA
BEGIN
    DECLARE v_total INT DEFAULT 0;
    SELECT COUNT(*) INTO v_total FROM estudios;
    RETURN v_total;
END $$
DELIMITER ;

DROP FUNCTION IF EXISTS `fn_total_cromosomas`;
DELIMITER $$
CREATE FUNCTION `fn_total_cromosomas`() RETURNS int
    READS SQL DATA
BEGIN
    DECLARE v_total INT DEFAULT 0;
    SELECT COUNT(*) INTO v_total FROM cromosomas;
    RETURN v_total;
END $$
DELIMITER ;

DROP FUNCTION IF EXISTS `fn_promedio_cromosomas_por_estudio`;
DELIMITER $$
CREATE FUNCTION `fn_promedio_cromosomas_por_estudio`() RETURNS decimal(8,2)
    READS SQL DATA
BEGIN
    DECLARE v_promedio DECIMAL(8,2) DEFAULT 0.00;
    SELECT COALESCE(AVG(cantidad_cromosomas), 0.00)
    INTO v_promedio
    FROM estudios
    WHERE cantidad_cromosomas IS NOT NULL;
    RETURN v_promedio;
END $$
DELIMITER ;

DROP FUNCTION IF EXISTS `fn_confianza_promedio`;
DELIMITER $$
CREATE FUNCTION `fn_confianza_promedio`(
    p_id_estudio INT
) RETURNS decimal(5,4)
    READS SQL DATA
BEGIN
    DECLARE v_promedio DECIMAL(5,4) DEFAULT 0.0000;
    SELECT COALESCE(AVG(confianza), 0.0000)
    INTO v_promedio
    FROM cromosomas
    WHERE id_estudio = p_id_estudio;
    RETURN v_promedio;
END $$
DELIMITER ;

DROP FUNCTION IF EXISTS `fn_estado_estudio`;
DELIMITER $$
CREATE FUNCTION `fn_estado_estudio`(
    p_id_estudio INT
) RETURNS varchar(20)
    READS SQL DATA
BEGIN
    DECLARE v_tiene_resultado INT DEFAULT 0;
    DECLARE v_cantidad INT DEFAULT 0;

    SELECT COUNT(*) INTO v_tiene_resultado
    FROM resultados
    WHERE id_estudio = p_id_estudio;

    IF v_tiene_resultado > 0 THEN
        RETURN 'FINALIZADO';
    END IF;

    SELECT COALESCE(cantidad_cromosomas, COUNT(*))
    INTO v_cantidad
    FROM estudios e
    LEFT JOIN cromosomas c ON c.id_estudio = e.id_estudio
    WHERE e.id_estudio = p_id_estudio
    GROUP BY e.cantidad_cromosomas;

    IF v_cantidad > 0 THEN
        RETURN 'PROCESADO';
    END IF;

    RETURN 'PENDIENTE';
END $$
DELIMITER ;

-- Procedimientos almacenados (máximo 4 para MVP)
DROP PROCEDURE IF EXISTS `sp_guardar_analisis_completo`;
DELIMITER $$
CREATE PROCEDURE `sp_guardar_analisis_completo`(
    IN p_imagen_original VARCHAR(255),
    IN p_imagen_resultado VARCHAR(255),
    IN p_detecciones JSON,
    OUT p_id_estudio INT
)
BEGIN
    DECLARE v_total_detecciones INT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_detecciones IS NULL OR JSON_TYPE(p_detecciones) <> 'ARRAY' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'p_detecciones debe ser un arreglo JSON';
    END IF;

    SET v_total_detecciones = JSON_LENGTH(p_detecciones);

    START TRANSACTION;

    INSERT INTO estudios (
        imagen_original,
        cantidad_cromosomas,
        imagen_resultado
    )
    VALUES (
        p_imagen_original,
        v_total_detecciones,
        p_imagen_resultado
    );

    SET p_id_estudio = LAST_INSERT_ID();

    INSERT INTO cromosomas (
        id_estudio,
        clase_detectada,
        x,
        y,
        ancho,
        alto,
        confianza
    )
    SELECT
        p_id_estudio,
        jt.clase,
        jt.x,
        jt.y,
        jt.ancho,
        jt.alto,
        jt.confianza
    FROM JSON_TABLE(
        p_detecciones,
        '$[*]' COLUMNS (
            clase VARCHAR(50) PATH '$.clase',
            x INT PATH '$.x',
            y INT PATH '$.y',
            ancho INT PATH '$.ancho',
            alto INT PATH '$.alto',
            confianza DECIMAL(5,4) PATH '$.confianza'
        )
    ) AS jt;

    INSERT INTO clasificaciones (
        id_cromosoma,
        cromosoma_asignado,
        confianza
    )
    SELECT
        id_cromosoma,
        LEFT(clase_detectada, 5),
        confianza
    FROM cromosomas
    WHERE id_estudio = p_id_estudio;

    COMMIT;
END $$
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_guardar_revision_estudio`;
DELIMITER $$
CREATE PROCEDURE `sp_guardar_revision_estudio`(
    IN p_id_estudio INT,
    IN p_clasificaciones JSON,
    IN p_cariotipo VARCHAR(30),
    IN p_alteracion VARCHAR(100),
    IN p_observacion TEXT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF (SELECT COUNT(*) FROM estudios WHERE id_estudio = p_id_estudio) = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El estudio indicado no existe';
    END IF;

    IF p_clasificaciones IS NOT NULL
       AND JSON_TYPE(p_clasificaciones) <> 'ARRAY' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'p_clasificaciones debe ser un arreglo JSON';
    END IF;

    START TRANSACTION;

    IF p_clasificaciones IS NOT NULL THEN
        UPDATE clasificaciones cl
        INNER JOIN cromosomas c
            ON c.id_cromosoma = cl.id_cromosoma
        INNER JOIN JSON_TABLE(
            p_clasificaciones,
            '$[*]' COLUMNS (
                id_cromosoma INT PATH '$.id_cromosoma',
                cromosoma_asignado VARCHAR(5) PATH '$.cromosoma_asignado',
                confianza DECIMAL(5,4) PATH '$.confianza'
            )
        ) AS jt
            ON jt.id_cromosoma = cl.id_cromosoma
        SET cl.cromosoma_asignado = COALESCE(jt.cromosoma_asignado, cl.cromosoma_asignado),
            cl.confianza = COALESCE(jt.confianza, cl.confianza)
        WHERE c.id_estudio = p_id_estudio;

        INSERT INTO clasificaciones (
            id_cromosoma,
            cromosoma_asignado,
            confianza
        )
        SELECT
            c.id_cromosoma,
            COALESCE(jt.cromosoma_asignado, LEFT(c.clase_detectada, 5)),
            COALESCE(jt.confianza, c.confianza)
        FROM JSON_TABLE(
            p_clasificaciones,
            '$[*]' COLUMNS (
                id_cromosoma INT PATH '$.id_cromosoma',
                cromosoma_asignado VARCHAR(5) PATH '$.cromosoma_asignado',
                confianza DECIMAL(5,4) PATH '$.confianza'
            )
        ) AS jt
        INNER JOIN cromosomas c
            ON c.id_cromosoma = jt.id_cromosoma
        LEFT JOIN clasificaciones cl
            ON cl.id_cromosoma = c.id_cromosoma
        WHERE c.id_estudio = p_id_estudio
          AND cl.id_cromosoma IS NULL;
    END IF;

    INSERT INTO resultados (
        id_estudio,
        cariotipo,
        alteracion,
        observacion
    )
    VALUES (
        p_id_estudio,
        p_cariotipo,
        p_alteracion,
        p_observacion
    )
    ON DUPLICATE KEY UPDATE
        cariotipo = VALUES(cariotipo),
        alteracion = VALUES(alteracion),
        observacion = VALUES(observacion);

    COMMIT;
END $$
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_modificar_cromosoma`;
DELIMITER $$
CREATE PROCEDURE `sp_modificar_cromosoma`(
    IN p_id_cromosoma INT,
    IN p_clase VARCHAR(5)
)
BEGIN
    UPDATE cromosomas
    SET clase_detectada = p_clase
    WHERE id_cromosoma = p_id_cromosoma;

    INSERT INTO clasificaciones (id_cromosoma, cromosoma_asignado)
    VALUES (p_id_cromosoma, p_clase)
    ON DUPLICATE KEY UPDATE cromosoma_asignado = VALUES(cromosoma_asignado);
END $$
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_eliminar_cromosoma`;
DELIMITER $$
CREATE PROCEDURE `sp_eliminar_cromosoma`(
    IN p_id_cromosoma INT
)
BEGIN
    DECLARE v_id_estudio INT;

    SELECT id_estudio INTO v_id_estudio
    FROM cromosomas
    WHERE id_cromosoma = p_id_cromosoma;

    DELETE FROM clasificaciones WHERE id_cromosoma = p_id_cromosoma;
    DELETE FROM cromosomas WHERE id_cromosoma = p_id_cromosoma;

    IF v_id_estudio IS NOT NULL THEN
        UPDATE estudios
        SET cantidad_cromosomas = (SELECT COUNT(*) FROM cromosomas WHERE id_estudio = v_id_estudio)
        WHERE id_estudio = v_id_estudio;
    END IF;
END $$
DELIMITER ;

-- Vistas para consulta
DROP VIEW IF EXISTS `vista_resumen_estudios`;
CREATE VIEW `vista_resumen_estudios` AS
SELECT
    e.id_estudio,
    e.imagen_original,
    e.fecha_analisis,
    COALESCE(e.cantidad_cromosomas, (SELECT COUNT(*) FROM cromosomas c WHERE c.id_estudio = e.id_estudio)) AS total_detecciones,
    fn_confianza_promedio(e.id_estudio) AS confianza_promedio,
    fn_estado_estudio(e.id_estudio) AS estado,
    r.cariotipo,
    r.alteracion
FROM estudios e
LEFT JOIN resultados r ON r.id_estudio = e.id_estudio;

DROP VIEW IF EXISTS `vista_estadisticas_clase`;
CREATE VIEW `vista_estadisticas_clase` AS
SELECT
    id_estudio,
    clase_detectada,
    COUNT(*) AS cantidad,
    ROUND(AVG(confianza), 4) AS confianza_promedio,
    MIN(confianza) AS confianza_minima,
    MAX(confianza) AS confianza_maxima
FROM cromosomas
GROUP BY id_estudio, clase_detectada;

DROP VIEW IF EXISTS `vista_estadisticas_globales`;
CREATE VIEW `vista_estadisticas_globales` AS
SELECT
    fn_total_estudios() AS total_estudios,
    fn_total_cromosomas() AS total_cromosomas,
    fn_promedio_cromosomas_por_estudio() AS promedio_cromosomas_por_estudio;

DROP VIEW IF EXISTS `vista_estudios_por_estado`;
CREATE VIEW `vista_estudios_por_estado` AS
SELECT
    fn_estado_estudio(id_estudio) AS estado,
    COUNT(*) AS cantidad
FROM estudios
GROUP BY fn_estado_estudio(id_estudio);

DROP VIEW IF EXISTS `vista_clases_globales`;
CREATE VIEW `vista_clases_globales` AS
SELECT
    clase_detectada,
    COUNT(*) AS cantidad,
    ROUND(AVG(confianza), 4) AS confianza_promedio,
    MIN(confianza) AS confianza_minima,
    MAX(confianza) AS confianza_maxima
FROM cromosomas
GROUP BY clase_detectada;
